"""
Módulo de métricas para o parser de IA.
Coleta estatísticas de uso, sucessos e erros.
"""
import time
from collections import defaultdict

class MetricsCollector:
    def __init__(self):
        self.total_chamadas = 0
        self.sucessos = 0
        self.erros = 0
        self.ultimas_respostas = []  # armazena últimas 100 resultados (parcial)
        self.tempos = []  # tempos de resposta (últimos 100)

    def registrar_chamada(self, sucesso: bool, tempo: float = None):
        self.total_chamadas += 1
        if sucesso:
            self.sucessos += 1
        else:
            self.erros += 1
        if tempo is not None:
            self.tempos.append(tempo)
            if len(self.tempos) > 100:
                self.tempos.pop(0)

    def obter_resumo(self):
        taxa_sucesso = (self.sucessos / self.total_chamadas * 100) if self.total_chamadas > 0 else 0
        tempo_medio = sum(self.tempos) / len(self.tempos) if self.tempos else None
        return {
            'total_chamadas': self.total_chamadas,
            'sucessos': self.sucessos,
            'erros': self.erros,
            'taxa_sucesso': round(taxa_sucesso, 2),
            'tempo_medio_resposta': round(tempo_medio, 3) if tempo_medio else None
        }

metrics_collector = MetricsCollector()