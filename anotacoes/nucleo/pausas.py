"""
pausas.py
---------
Horários dos alertas de pausa do dia (sem interface, fácil de testar).

  14:40  Pausa NR 17
  17:00  Pausa para lanche
  18:10  Pausa NR 17

`pausa_devida` diz qual alerta deve aparecer agora; quem avisa o usuário é
interface/mixins/pausas.py.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

# Se o programa estava travado, o computador dormindo ou a janela ocupada, o
# alerta ainda aparece até este tempo depois do horário. Passou disso, o aviso
# perdeu o sentido ("pausa das 14:40" às 16:00) e é descartado.
TOLERANCIA_SEGUNDOS = 120


@dataclass(frozen=True)
class Pausa:
    hora: time
    tipo: str          # "nr17" ou "lanche"
    titulo: str
    mensagem: str

    @property
    def rotulo(self) -> str:
        return self.hora.strftime("%H:%M")


PAUSAS = (
    Pausa(time(14, 40), "nr17", "Pausa NR 17",
          "Hora da pausa da NR 17. Levante-se, alongue-se e descanse a vista e as mãos "
          "por alguns minutos."),
    Pausa(time(17, 0), "lanche", "Pausa para lanche",
          "Hora da pausa para o lanche. Aproveite para comer e se hidratar."),
    Pausa(time(18, 10), "nr17", "Pausa NR 17",
          "Hora da pausa da NR 17. Levante-se, alongue-se e descanse a vista e as mãos "
          "por alguns minutos."),
)


def pausa_devida(agora: datetime, ja_avisadas: set) -> Optional[Pausa]:
    """Pausa cujo horário já chegou (e ainda está dentro da tolerância) e que
    não foi avisada hoje. `ja_avisadas` guarda pares (data, "HH:MM")."""
    for pausa in PAUSAS:
        if (agora.date(), pausa.rotulo) in ja_avisadas:
            continue
        atraso = (agora - datetime.combine(agora.date(), pausa.hora)).total_seconds()
        if 0 <= atraso <= TOLERANCIA_SEGUNDOS:
            return pausa
    return None


def marcar_avisada(ja_avisadas: set, pausa: Pausa, dia: date) -> None:
    """Registra a pausa como avisada no dia e esquece os dias anteriores."""
    ja_avisadas.difference_update({c for c in ja_avisadas if c[0] != dia})
    ja_avisadas.add((dia, pausa.rotulo))
