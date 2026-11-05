"""
database.py
-----------
Camada de persistência do sistema de anotações hospitalares.

Usa SQLite (módulo `sqlite3` da biblioteca padrão), portanto não exige
servidor externo nem instalação adicional.

O banco é criado automaticamente na primeira execução, em uma pasta
"dados" ao lado do executável (ou ao lado deste arquivo, em desenvolvimento).
"""

import os
import sqlite3
import sys
import unicodedata
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

# ----------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------
STATUS_PENDENTE = "Pendente"
STATUS_ATENDIDA = "Atendida"

# Limites de tamanho (também validados na interface)
MAX_NOME = 120
MAX_CONTATO = 80
MAX_DESCRICAO = 2000

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS solicitacoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora     TEXT    NOT NULL,
    nome_paciente TEXT    NOT NULL,
    contato       TEXT,
    descricao     TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'Pendente'
                  CHECK (status IN ('Pendente', 'Atendida'))
);

CREATE INDEX IF NOT EXISTS idx_solicitacoes_nome
    ON solicitacoes (nome_paciente);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_contato
    ON solicitacoes (contato);
"""

# Tipo auxiliar: (id, data_hora, nome_paciente, contato, descricao, status)
Registro = Tuple[int, str, str, str, str, str]


NOME_ARQUIVO = "anotacoes_hospitalares.db"


def normalizar(texto) -> str:
    """Minúsculas e sem acentos: 'JOÃO' -> 'joao' (usado na busca)."""
    decomposto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def _escapar_like(texto: str) -> str:
    """Faz % e _ digitados pelo usuário valerem como texto comum."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _pasta_gravavel(pasta: str) -> bool:
    """True se for possível criar a pasta e gravar arquivos nela."""
    try:
        os.makedirs(pasta, exist_ok=True)
        teste = os.path.join(pasta, ".teste_gravacao")
        with open(teste, "w", encoding="utf-8") as arq:
            arq.write("ok")
        os.remove(teste)
        return True
    except OSError:
        return False


def caminho_banco() -> str:
    """
    Define onde o arquivo .db fica salvo.

    Ordem de preferência (usa a primeira pasta com permissão de gravação):
      1. pasta "dados" ao lado do .exe (ou deste arquivo, em desenvolvimento);
      2. %LOCALAPPDATA%\\AnotacoesHospitalares;
      3. pasta do usuário.
    """
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    candidatas = [os.path.join(base, "dados")]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidatas.append(os.path.join(local, "AnotacoesHospitalares"))
    candidatas.append(os.path.join(os.path.expanduser("~"), "AnotacoesHospitalares"))

    for pasta in candidatas:
        if _pasta_gravavel(pasta):
            return os.path.join(pasta, NOME_ARQUIVO)
    raise OSError("Nenhuma pasta com permissão de gravação foi encontrada para o banco de dados.")


class Database:
    """Encapsula todas as operações com o banco SQLite."""

    def __init__(self, caminho: Optional[str] = None) -> None:
        self.caminho = caminho or caminho_banco()
        self._inicializar()

    # ------------------------------------------------------------------
    # Infraestrutura
    # ------------------------------------------------------------------
    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.caminho, timeout=10)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.create_function("norm", 1, normalizar)  # busca sem acentos
        return conn

    def _inicializar(self) -> None:
        """Cria a tabela e os índices automaticamente, se não existirem."""
        conn = self._conectar()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def _executar(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Executa um comando de escrita, confirma e FECHA a conexão.

        (O `with conn:` do sqlite3 só confirma a transação; não fecha o
        arquivo. No Windows, conexões abertas podem travar o .db.)
        """
        conn = self._conectar()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur
        finally:
            conn.close()

    def _consultar(self, sql: str, params: tuple = ()) -> list:
        conn = self._conectar()
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------
    def inserir(self, nome_paciente: str, contato: str, descricao: str) -> int:
        """Insere uma nova solicitação (status inicial: Pendente).

        A data/hora é gerada automaticamente. Retorna o id criado.
        Lança ValueError se nome ou descrição estiverem vazios, ou se
        algum campo ultrapassar o tamanho máximo.
        """
        nome = (nome_paciente or "").strip()
        cont = (contato or "").strip()
        desc = (descricao or "").strip()

        if not nome or not desc:
            raise ValueError("Nome do paciente e descrição são obrigatórios.")
        if len(nome) > MAX_NOME:
            raise ValueError(f"O nome deve ter no máximo {MAX_NOME} caracteres.")
        if len(cont) > MAX_CONTATO:
            raise ValueError(f"O contato deve ter no máximo {MAX_CONTATO} caracteres.")
        if len(desc) > MAX_DESCRICAO:
            raise ValueError(
                f"A descrição deve ter no máximo {MAX_DESCRICAO} caracteres."
            )

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self._executar(
            """
            INSERT INTO solicitacoes
                (data_hora, nome_paciente, contato, descricao, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (data_hora, nome, cont, desc, STATUS_PENDENTE),
        )
        return int(cur.lastrowid)

    def listar(
        self,
        filtro: str = "",
        status: Optional[str] = None,
        limite: Optional[int] = None,
    ) -> List[Registro]:
        """Lista registros, do mais recente ao mais antigo.

        `filtro` busca no nome ou no contato, sem diferenciar maiúsculas nem acentos.
        `status` (opcional) restringe a "Pendente" ou "Atendida".
        `limite` (opcional) devolve apenas os N registros mais recentes.
        Consulta parametrizada: protegida contra SQL injection.
        """
        filtro = (filtro or "").strip()
        condicoes: list = []
        params: list = []

        if filtro:
            condicoes.append(
                "(norm(nome_paciente) LIKE ? ESCAPE '\\' "
                "OR norm(contato) LIKE ? ESCAPE '\\')"
            )
            termo = f"%{_escapar_like(normalizar(filtro))}%"
            params.extend([termo, termo])
        if status:
            if status not in (STATUS_PENDENTE, STATUS_ATENDIDA):
                raise ValueError(f"Status inválido: {status}")
            condicoes.append("status = ?")
            params.append(status)

        sql = (
            "SELECT id, data_hora, nome_paciente, contato, descricao, status "
            "FROM solicitacoes"
        )
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        sql += " ORDER BY data_hora DESC, id DESC"
        if limite is not None:
            sql += " LIMIT ?"
            params.append(int(limite))

        return self._consultar(sql, tuple(params))

    def atualizar_status(self, registro_id: int, novo_status: str) -> None:
        """Altera o status de uma solicitação (Pendente / Atendida)."""
        if novo_status not in (STATUS_PENDENTE, STATUS_ATENDIDA):
            raise ValueError(f"Status inválido: {novo_status}")
        self._executar(
            "UPDATE solicitacoes SET status = ? WHERE id = ?",
            (novo_status, registro_id),
        )

    def excluir(self, registro_id: int) -> bool:
        """Exclui uma solicitação. Retorna True se algum registro foi removido."""
        cur = self._executar(
            "DELETE FROM solicitacoes WHERE id = ?", (registro_id,)
        )
        return cur.rowcount > 0

    def excluir_varios(self, ids: Iterable[int]) -> int:
        """Exclui várias solicitações de uma vez. Retorna quantas foram removidas."""
        ids = [int(i) for i in ids]
        if not ids:
            return 0
        marcadores = ",".join("?" for _ in ids)
        cur = self._executar(
            f"DELETE FROM solicitacoes WHERE id IN ({marcadores})", tuple(ids)
        )
        return cur.rowcount

    def obter(self, registro_id: int) -> Optional[Registro]:
        """Retorna um registro pelo id (ou None)."""
        linhas = self._consultar(
            "SELECT id, data_hora, nome_paciente, contato, descricao, status "
            "FROM solicitacoes WHERE id = ?",
            (registro_id,),
        )
        return linhas[0] if linhas else None

    def contar_por_status(self) -> dict:
        """Retorna {'Pendente': n, 'Atendida': m} para o painel de resumo."""
        resultado = {STATUS_PENDENTE: 0, STATUS_ATENDIDA: 0}
        for status, total in self._consultar(
            "SELECT status, COUNT(*) FROM solicitacoes GROUP BY status"
        ):
            resultado[status] = total
        return resultado

    def contar_hoje(self) -> int:
        """Quantidade de solicitações registradas na data de hoje."""
        hoje = datetime.now().strftime("%Y-%m-%d")
        linhas = self._consultar(
            "SELECT COUNT(*) FROM solicitacoes WHERE substr(data_hora, 1, 10) = ?",
            (hoje,),
        )
        return int(linhas[0][0])
