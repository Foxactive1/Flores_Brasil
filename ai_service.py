# ai_service.py
"""
Camada de Inteligência Artificial — Flores Brasil
Integração com Groq API com fallback e tratamento robusto de erros.
"""

import os
import json
import logging
import time
import re
from typing import Optional
from groq import Groq, APIError, APITimeoutError, RateLimitError
from metrics import metrics_collector

logger = logging.getLogger(__name__)

# ─── CONFIGURAÇÃO ────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
MAX_TOKENS = 2500

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ─── SCHEMA DO PEDIDO ────────────────────────────────────────

PEDIDO_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_mensagem": {"type": "string", "enum": ["pedido", "orcamento", "duvida", "reclamacao", "cancelamento", "outro"]},
        "confianca": {"type": "number", "minimum": 0, "maximum": 1},
        "sentimento": {"type": "string", "enum": ["positivo", "neutro", "negativo", "urgente"]},
        "avisos": {"type": "array", "items": {"type": "string"}},
        "codigo": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "cliente": {"type": ["string", "null"]},
        "telefone": {"type": ["string", "null"]},
        "endereco": {
            "type": "object",
            "properties": {
                "logradouro": {"type": ["string", "null"]},
                "numero": {"type": ["string", "null"]},
                "complemento": {"type": ["string", "null"]},
                "bairro": {"type": ["string", "null"]},
                "cidade": {"type": ["string", "null"]},
                "estado": {"type": ["string", "null"]},
                "cep": {"type": ["string", "null"]},
                "referencia": {"type": ["string", "null"]},
                "completo": {"type": ["string", "null"]}
            },
            "required": ["logradouro", "numero", "complemento", "bairro", "cidade", "estado", "cep", "referencia", "completo"],
            "additionalProperties": False
        },
        "mensagem_cartao": {"type": ["string", "null"]},
        "itens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "emoji": {"type": "string"},
                    "nome": {"type": "string"},
                    "qtd": {"type": "integer", "minimum": 1},
                    "preco_unitario": {"type": "number"},
                    "preco_formatado": {"type": "string"},
                    "subtotal": {"type": "number"},
                    "observacao_item": {"type": ["string", "null"]}
                },
                "required": ["emoji", "nome", "qtd", "preco_unitario", "preco_formatado", "subtotal", "observacao_item"],
                "additionalProperties": False
            }
        },
        "subtotal": {"type": ["number", "null"]},
        "entrega": {"type": ["string", "null"]},
        "entrega_valor": {"type": ["number", "null"]},
        "total": {"type": ["number", "null"]},
        "total_formatado": {"type": ["string", "null"]},
        "observacao": {"type": ["string", "null"]},
        "resposta_sugerida": {"type": ["string", "null"]}
    },
    "required": [
        "tipo_mensagem", "confianca", "sentimento", "avisos",
        "codigo", "status", "cliente", "telefone",
        "endereco", "mensagem_cartao", "itens",
        "subtotal", "entrega", "entrega_valor", "total", "total_formatado",
        "observacao", "resposta_sugerida"
    ],
    "additionalProperties": False
}

# ─── SYSTEM PROMPT ───────────────────────────────────────────

SYSTEM_PROMPT = """Você é um parser de pedidos de floricultura. Extraia dados estruturados de mensagens de WhatsApp.

Regras:
- Itens: emoji, nome, quantidade, preço unitário (ex: 89.00), preço_formatado (ex: "R$ 89,00"), subtotal (preco * qtd).
- Endereço: decomponha em logradouro, número, complemento, bairro, cidade, estado, CEP e campo "completo" com o endereço completo.
- Valores: use números sem formatação (ex: 89.00). Para formatação use "R$ 89,00".
- Se faltar dado, use null.
- Classifique tipo_mensagem: pedido, orcamento, duvida, reclamacao, cancelamento, outro.
- Confiança: 0-1.
- Avisos: liste problemas (ex: "endereço incompleto").
- Resposta sugerida: cordial e útil.

Responda APENAS JSON válido, sem markdown ou texto extra."""

# ─── FUNÇÃO PRINCIPAL ────────────────────────────────────────

def parsear_mensagem(mensagem: str, timeout: float = 30.0) -> dict:
    inicio = time.perf_counter()

    def registrar(sucesso: bool):
        metrics_collector.registrar_chamada(sucesso, time.perf_counter() - inicio)

    if not client:
        logger.warning("GROQ_API_KEY não configurada, usando fallback regex")
        registrar(False)
        return _fallback_regex(mensagem)

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            logger.info("[AI] Tentativa %s/%s (%s caracteres)", attempt+1, MAX_RETRIES, len(mensagem))

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=0.05,
                max_tokens=MAX_TOKENS,
                timeout=timeout,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": mensagem}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "pedido_flores_brasil",
                        "strict": False,
                        "schema": PEDIDO_SCHEMA
                    }
                }
            )

            raw = response.choices[0].message.content or "{}"
            raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
            pedido = json.loads(raw)
            pedido = _validar_e_completar(pedido, mensagem)

            logger.info("[AI] Sucesso | tipo=%s | confiança=%s | itens=%s",
                        pedido.get("tipo_mensagem"), pedido.get("confianca"), len(pedido.get("itens", [])))
            registrar(True)
            return pedido

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning("[AI] JSON inválido: %s", e)
            if attempt == MAX_RETRIES - 1:
                break

        except RateLimitError as e:
            last_error = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("[AI] Rate limit. Retry em %.1fs", delay)
            time.sleep(delay)

        except APITimeoutError as e:
            last_error = e
            logger.warning("[AI] Timeout: %s", e)

        except APIError as e:
            last_error = e
            logger.error("[AI] API Error: %s", e)

            if "json_validate_failed" in str(e):
                logger.warning("[AI] Erro de validação JSON. Tentando com temperatura 0.0")
                try:
                    response = client.chat.completions.create(
                        model=GROQ_MODEL,
                        temperature=0.0,
                        max_tokens=MAX_TOKENS,
                        timeout=timeout,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": mensagem}
                        ],
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "pedido_flores_brasil",
                                "strict": False,
                                "schema": PEDIDO_SCHEMA
                            }
                        }
                    )
                    raw = response.choices[0].message.content or "{}"
                    raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
                    pedido = json.loads(raw)
                    pedido = _validar_e_completar(pedido, mensagem)
                    registrar(True)
                    return pedido
                except Exception as e2:
                    logger.warning("[AI] Tentativa com temperatura 0.0 também falhou: %s", e2)
                    last_error = e2

            if "decommissioned" in str(e) or "not support response format" in str(e):
                logger.warning("[AI] Modelo incompatível. Usando fallback.")
                break

            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))

        except Exception as e:
            last_error = e
            logger.exception("[AI] Erro inesperado")
            registrar(False)
            raise

    logger.error("[AI] Todas as tentativas falharam: %s", last_error)
    resultado = _fallback_regex(mensagem)
    resultado["avisos"].append(f"⚠️ IA indisponível — dados extraídos por regex: {last_error}")
    registrar(False)
    return resultado

# ─── VALIDAÇÃO E COMPLEMENTAÇÃO ─────────────────────────────

def _validar_e_completar(pedido: dict, mensagem_original: str) -> dict:
    avisos = pedido.get("avisos", [])

    # Garantir itens
    if not pedido.get("itens"):
        pedido["itens"] = []

    # Calcular subtotal se não vier
    if pedido.get("subtotal") is None and pedido["itens"]:
        soma = sum(item.get("subtotal", 0) for item in pedido["itens"])
        pedido["subtotal"] = soma

    # Calcular total se não vier
    if pedido.get("total") is None:
        subtotal = pedido.get("subtotal") or 0
        entrega = pedido.get("entrega_valor") or 0
        pedido["total"] = subtotal + entrega
        pedido["total_formatado"] = f"R$ {pedido['total']:.2f}".replace('.', ',')

    # Endereço: só avisa se o campo 'completo' estiver vazio
    endereco = pedido.get("endereco", {})
    if not endereco.get("completo"):
        avisos.append("Endereço não informado")
    # Se completo existe, não geramos aviso sobre campos individuais

    # Telefone
    if pedido.get("telefone"):
        digitos = ''.join(filter(str.isdigit, pedido["telefone"]))
        if len(digitos) < 10:
            avisos.append("Telefone possivelmente inválido")

    if pedido.get("confianca", 0) < 0.5:
        avisos.append("⚠️ Baixa confiança — revisão manual recomendada")

    # Preencher defaults
    pedido.setdefault("tipo_mensagem", "outro")
    pedido.setdefault("confianca", 0.5)
    pedido.setdefault("sentimento", "neutro")
    pedido.setdefault("avisos", avisos)
    pedido.setdefault("endereco", {})
    pedido.setdefault("codigo", None)
    pedido.setdefault("status", None)
    pedido.setdefault("cliente", None)
    pedido.setdefault("telefone", None)
    pedido.setdefault("mensagem_cartao", None)
    pedido.setdefault("entrega", None)
    pedido.setdefault("observacao", None)
    pedido.setdefault("resposta_sugerida", None)

    return pedido

# ─── FALLBACK REGEX MELHORADO ──────────────────────────────

def _fallback_regex(mensagem: str) -> dict:
    resultado = {
        "tipo_mensagem": "pedido",
        "confianca": 0.3,
        "sentimento": "neutro",
        "avisos": ["Extração por regex — dados podem estar incompletos"],
        "codigo": None,
        "status": None,
        "cliente": None,
        "telefone": None,
        "endereco": {
            "logradouro": None, "numero": None, "complemento": None,
            "bairro": None, "cidade": None, "estado": None,
            "cep": None, "referencia": None, "completo": None
        },
        "mensagem_cartao": None,
        "itens": [],
        "subtotal": None,
        "entrega": None,
        "entrega_valor": None,
        "total": None,
        "total_formatado": None,
        "observacao": None,
        "resposta_sugerida": None
    }

    # Código
    m = re.search(r'\*Código:\*\s*#?(\w+)', mensagem, re.I)
    if m:
        resultado["codigo"] = m.group(1)

    # Status
    m = re.search(r'\*Status:\*\s*(\w+)', mensagem, re.I)
    if m:
        resultado["status"] = m.group(1)

    # Cliente
    m = re.search(r'👤\s*\*Cliente:\*\s*(.+)', mensagem, re.I)
    if m:
        resultado["cliente"] = m.group(1).strip()

    # Telefone
    m = re.search(r'📞\s*\*Telefone:\*\s*(.+)', mensagem, re.I)
    if m:
        resultado["telefone"] = m.group(1).strip()

    # ─── EXTRAÇÃO DE ENDEREÇO MELHORADA ──────────────────
    m = re.search(r'📍\s*\*Endereço.*?:\*\s*\n?(.+)', mensagem, re.I | re.S)
    if m:
        endereco_texto = m.group(1).strip().split('\n')[0]
        resultado["endereco"]["completo"] = endereco_texto

        # Extrai CEP
        cep_match = re.search(r'CEP:\s*(\d{5,8})', endereco_texto, re.I)
        if cep_match:
            resultado["endereco"]["cep"] = cep_match.group(1)

        # Remove CEP para simplificar
        endereco_sem_cep = re.sub(r',?\s*CEP:\s*\d{5,8}', '', endereco_texto, flags=re.I)

        # Divide por vírgula e hífen
        partes = re.split(r',\s*|\s*-\s*', endereco_sem_cep)
        # Exemplo: ["Vergílio José Gomes", "2652", "Jardim Luiza 1", "Franca", "SP"]
        if len(partes) >= 1:
            resultado["endereco"]["logradouro"] = partes[0].strip()
        if len(partes) >= 2:
            # Verifica se é número
            if partes[1].strip().replace('.', '').isdigit():
                resultado["endereco"]["numero"] = partes[1].strip()
            else:
                resultado["endereco"]["complemento"] = partes[1].strip()
        if len(partes) >= 3:
            if resultado["endereco"]["numero"] is None and partes[1].strip().replace('.', '').isdigit():
                resultado["endereco"]["numero"] = partes[1].strip()
            if not partes[2].strip().replace('.', '').isdigit():
                resultado["endereco"]["bairro"] = partes[2].strip()
        if len(partes) >= 4:
            cidade_uf = partes[3].strip().split('-')
            if len(cidade_uf) == 2:
                resultado["endereco"]["cidade"] = cidade_uf[0].strip()
                resultado["endereco"]["estado"] = cidade_uf[1].strip()
            else:
                resultado["endereco"]["cidade"] = cidade_uf[0].strip()
        if len(partes) >= 5:
            if resultado["endereco"]["estado"] is None:
                resultado["endereco"]["estado"] = partes[4].strip()

    # Total
    m = re.search(r'\*TOTAL:\s*R\$\s*([\d.,]+)\*', mensagem, re.I)
    if m:
        total_str = m.group(1)
        total_clean = _parse_brasileiro(total_str)
        if total_clean is not None:
            resultado["total"] = total_clean
            resultado["total_formatado"] = f"R$ {total_clean:.2f}".replace('.', ',')

    # Itens
    itens_pattern = re.findall(
        r'([\U0001F300-\U0001FAFF])\s*\*(.+?)\*\s*×\s*(\d+)\s*[—\-]\s*R\$\s*([\d.,]+)',
        mensagem
    )
    for emoji, nome, qtd, preco in itens_pattern:
        preco_clean = _parse_brasileiro(preco)
        if preco_clean is not None:
            qtd_int = int(qtd)
            resultado["itens"].append({
                "emoji": emoji,
                "nome": nome.strip(),
                "qtd": qtd_int,
                "preco_unitario": preco_clean / qtd_int if qtd_int > 0 else preco_clean,
                "preco_formatado": f"R$ {preco_clean:.2f}".replace('.', ','),
                "subtotal": preco_clean,
                "observacao_item": None
            })

    # Mensagem no cartão
    m = re.search(r'💌\s*\*Mensagem no cartão:\*\s*\n?"(.+?)"', mensagem, re.I | re.S)
    if m:
        resultado["mensagem_cartao"] = m.group(1).strip()

    # Calcula subtotal e total se itens existirem
    if resultado["itens"]:
        subtotal = sum(item["subtotal"] for item in resultado["itens"])
        resultado["subtotal"] = subtotal
        if resultado["total"] is None:
            resultado["total"] = subtotal
            resultado["total_formatado"] = f"R$ {subtotal:.2f}".replace('.', ',')

    return resultado

# ─── UTILITÁRIO ──────────────────────────────────────────────

def _parse_brasileiro(valor: str) -> Optional[float]:
    if not valor:
        return None
    v = valor.strip()
    v = re.sub(r'R?\$', '', v).strip()
    if ',' in v and '.' in v:
        v = v.replace('.', '').replace(',', '.')
    elif ',' in v:
        v = v.replace(',', '.')
    try:
        return float(v)
    except ValueError:
        return None