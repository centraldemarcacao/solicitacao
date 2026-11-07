"""
database.py
-----------
Camada de persistência do sistema de anotações.

Usa SQLite (módulo `sqlite3` da biblioteca padrão), portanto não exige
servidor externo nem instalação adicional.

O banco é criado automaticamente na primeira execução, em uma pasta
"dados" ao lado do executável (ou ao lado deste arquivo, em desenvolvimento).

Recursos:
  - edição de registros;
  - exclusão reversível (lixeira, com limpeza automática após alguns dias);
  - backups consistentes (API de backup do SQLite) com rotação e restauração;
  - migração automática de bancos criados por versões anteriores.
"""

import os
import sqlite3
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
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

DIAS_LIXEIRA = 30        # dias que um registro excluído fica na lixeira
BACKUPS_MANTER = 14      # quantidade de backups "backup_*.db" guardados
SEGURANCA_MANTER = 5     # cópias "antes_da_restauracao_*.db" guardadas
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"
NOME_ARQUIVO = "anotacoes_hospitalares.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS solicitacoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora     TEXT    NOT NULL,
    nome_paciente TEXT    NOT NULL,
    contato       TEXT,
    descricao     TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'Pendente'
                  CHECK (status IN ('Pendente', 'Atendida')),
    editado_em    TEXT,
    excluido_em   TEXT
);

CREATE INDEX IF NOT EXISTS idx_solicitacoes_nome
    ON solicitacoes (nome_paciente);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_contato
    ON solicitacoes (contato);
"""

# Colunas acrescentadas depois da versão 1 (migradas em bancos antigos)
COLUNAS_NOVAS = ("editado_em", "excluido_em")

# Tipo auxiliar: (id, data_hora, nome_paciente, contato, descricao, status)
Registro = Tuple[int, str, str, str, str, str]


# ----------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------
def agora() -> str:
    return datetime.now().strftime(FORMATO_DATA)


def normalizar(texto) -> str:
    """Minúsculas e sem acentos: 'JOÃO' -> 'joao' (usado na busca)."""
    decomposto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def _escapar_like(texto: str) -> str:
    """Faz % e _ digitados pelo usuário valerem como texto comum."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def validar_campos(nome: str, contato: str, descricao: str) -> dict:
    """Valida os campos de um registro. Retorna {campo: mensagem} (vazio = ok).

    Os campos esperados já devem vir sem espaços nas pontas.
    """
    erros = {}
    if not nome:
        erros["nome"] = "Informe o nome do paciente."
    elif len(nome) > MAX_NOME:
        erros["nome"] = f"Use no máximo {MAX_NOME} caracteres."
    if len(contato) > MAX_CONTATO:
        erros["contato"] = f"Use no máximo {MAX_CONTATO} caracteres."
    if not descricao:
        erros["descricao"] = "Descreva a solicitação."
    elif len(descricao) > MAX_DESCRICAO:
        erros["descricao"] = f"Use no máximo {MAX_DESCRICAO} caracteres."
    return erros


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


# ======================================================================
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
        """Cria a tabela (se não existir) e migra bancos de versões anteriores."""
        conn = self._conectar()
        try:
            conn.executescript(SCHEMA_SQL)
            existentes = {linha[1] for linha in conn.execute("PRAGMA table_info(solicitacoes)")}
            for coluna in COLUNAS_NOVAS:
                if coluna not in existentes:
                    conn.execute(f"ALTER TABLE solicitacoes ADD COLUMN {coluna} TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_solicitacoes_excluido "
                "ON solicitacoes (excluido_em)"
            )
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

    @staticmethod
    def _marcadores(ids: Iterable[int]):
        lista = [int(i) for i in ids]
        return lista, ",".join("?" for _ in lista)

    # ------------------------------------------------------------------
    # Criar, editar e consultar
    # ------------------------------------------------------------------
    @staticmethod
    def _validar(nome: str, contato: str, descricao: str):
        nome = (nome or "").strip()
        contato = (contato or "").strip()
        descricao = (descricao or "").strip()
        erros = validar_campos(nome, contato, descricao)
        if erros:
            raise ValueError(next(iter(erros.values())))
        return nome, contato, descricao

    def inserir(self, nome_paciente: str, contato: str, descricao: str) -> int:
        """Insere uma nova solicitação (status inicial: Pendente).

        A data/hora é gerada automaticamente. Retorna o id criado.
        Lança ValueError se algum campo for inválido.
        """
        nome, contato, descricao = self._validar(nome_paciente, contato, descricao)
        cur = self._executar(
            """
            INSERT INTO solicitacoes
                (data_hora, nome_paciente, contato, descricao, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agora(), nome, contato, descricao, STATUS_PENDENTE),
        )
        return int(cur.lastrowid)

    def atualizar(self, registro_id: int, nome_paciente: str, contato: str,
                  descricao: str) -> bool:
        """Edita nome, contato e descrição. Retorna False se o registro não existir
        (ou estiver na lixeira). Lança ValueError se algum campo for inválido."""
        nome, contato, descricao = self._validar(nome_paciente, contato, descricao)
        cur = self._executar(
            """
            UPDATE solicitacoes
               SET nome_paciente = ?, contato = ?, descricao = ?, editado_em = ?
             WHERE id = ? AND excluido_em IS NULL
            """,
            (nome, contato, descricao, agora(), int(registro_id)),
        )
        return cur.rowcount > 0

    def listar(
        self,
        filtro: str = "",
        status: Optional[str] = None,
        limite: Optional[int] = None,
    ) -> List[Registro]:
        """Lista registros (fora da lixeira), do mais recente ao mais antigo.

        `filtro` busca no nome ou no contato, sem diferenciar maiúsculas nem acentos.
        `status` (opcional) restringe a "Pendente" ou "Atendida".
        `limite` (opcional) devolve apenas os N registros mais recentes.
        Consulta parametrizada: protegida contra SQL injection.
        """
        filtro = (filtro or "").strip()
        condicoes: list = ["excluido_em IS NULL"]
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
            "FROM solicitacoes WHERE " + " AND ".join(condicoes) +
            " ORDER BY data_hora DESC, id DESC"
        )
        if limite is not None:
            sql += " LIMIT ?"
            params.append(int(limite))
        return self._consultar(sql, tuple(params))

    def obter(self, registro_id: int) -> Optional[Registro]:
        """Retorna um registro (fora da lixeira) pelo id, ou None."""
        linhas = self._consultar(
            "SELECT id, data_hora, nome_paciente, contato, descricao, status "
            "FROM solicitacoes WHERE id = ? AND excluido_em IS NULL",
            (int(registro_id),),
        )
        return linhas[0] if linhas else None

    def obter_detalhado(self, registro_id: int, incluir_excluidos: bool = False) -> Optional[dict]:
        """Como `obter`, mas devolve um dicionário com todas as colunas
        (inclusive `editado_em` e `excluido_em`)."""
        sql = (
            "SELECT id, data_hora, nome_paciente, contato, descricao, status, "
            "editado_em, excluido_em FROM solicitacoes WHERE id = ?"
        )
        if not incluir_excluidos:
            sql += " AND excluido_em IS NULL"
        linhas = self._consultar(sql, (int(registro_id),))
        if not linhas:
            return None
        chaves = ("id", "data_hora", "nome", "contato", "descricao", "status",
                  "editado_em", "excluido_em")
        return dict(zip(chaves, linhas[0]))

    def atualizar_status(self, registro_id: int, novo_status: str) -> None:
        """Altera o status de uma solicitação (Pendente / Atendida)."""
        if novo_status not in (STATUS_PENDENTE, STATUS_ATENDIDA):
            raise ValueError(f"Status inválido: {novo_status}")
        self._executar(
            "UPDATE solicitacoes SET status = ? WHERE id = ? AND excluido_em IS NULL",
            (novo_status, int(registro_id)),
        )

    def contar_por_status(self) -> dict:
        """Retorna {'Pendente': n, 'Atendida': m} (sem contar a lixeira)."""
        resultado = {STATUS_PENDENTE: 0, STATUS_ATENDIDA: 0}
        for status, total in self._consultar(
            "SELECT status, COUNT(*) FROM solicitacoes "
            "WHERE excluido_em IS NULL GROUP BY status"
        ):
            resultado[status] = total
        return resultado

    def contar_hoje(self) -> int:
        """Quantidade de solicitações registradas hoje (sem contar a lixeira)."""
        hoje = datetime.now().strftime("%Y-%m-%d")
        linhas = self._consultar(
            "SELECT COUNT(*) FROM solicitacoes "
            "WHERE excluido_em IS NULL AND substr(data_hora, 1, 10) = ?",
            (hoje,),
        )
        return int(linhas[0][0])

    def total_registros(self) -> int:
        """Total de linhas na tabela, inclusive a lixeira."""
        return int(self._consultar("SELECT COUNT(*) FROM solicitacoes")[0][0])

    # ------------------------------------------------------------------
    # Lixeira (exclusão reversível)
    # ------------------------------------------------------------------
    def excluir(self, registro_id: int) -> bool:
        """Move um registro para a lixeira. True se ele foi movido."""
        return self.excluir_varios([registro_id]) > 0

    def excluir_varios(self, ids: Iterable[int]) -> int:
        """Move vários registros para a lixeira. Retorna quantos foram movidos."""
        lista, marcadores = self._marcadores(ids)
        if not lista:
            return 0
        cur = self._executar(
            "UPDATE solicitacoes SET excluido_em = ? "
            f"WHERE excluido_em IS NULL AND id IN ({marcadores})",
            (agora(), *lista),
        )
        return cur.rowcount

    def listar_lixeira(self) -> list:
        """Registros na lixeira (mais recentemente excluídos primeiro):
        (id, data_hora, nome, contato, descricao, status, excluido_em)."""
        return self._consultar(
            "SELECT id, data_hora, nome_paciente, contato, descricao, status, excluido_em "
            "FROM solicitacoes WHERE excluido_em IS NOT NULL "
            "ORDER BY excluido_em DESC, id DESC"
        )

    def contar_lixeira(self) -> int:
        return int(self._consultar(
            "SELECT COUNT(*) FROM solicitacoes WHERE excluido_em IS NOT NULL"
        )[0][0])

    def restaurar(self, ids: Iterable[int]) -> int:
        """Tira registros da lixeira. Retorna quantos foram restaurados."""
        lista, marcadores = self._marcadores(ids)
        if not lista:
            return 0
        cur = self._executar(
            "UPDATE solicitacoes SET excluido_em = NULL "
            f"WHERE excluido_em IS NOT NULL AND id IN ({marcadores})",
            tuple(lista),
        )
        return cur.rowcount

    def apagar_definitivamente(self, ids: Iterable[int]) -> int:
        """Apaga de vez registros que JÁ estão na lixeira (nunca os demais)."""
        lista, marcadores = self._marcadores(ids)
        if not lista:
            return 0
        cur = self._executar(
            "DELETE FROM solicitacoes "
            f"WHERE excluido_em IS NOT NULL AND id IN ({marcadores})",
            tuple(lista),
        )
        return cur.rowcount

    def esvaziar_lixeira(self) -> int:
        cur = self._executar("DELETE FROM solicitacoes WHERE excluido_em IS NOT NULL")
        return cur.rowcount

    def limpar_lixeira_antiga(self, dias: int = DIAS_LIXEIRA) -> int:
        """Apaga da lixeira o que foi excluído há mais de `dias` dias."""
        limite = (datetime.now() - timedelta(days=dias)).strftime(FORMATO_DATA)
        cur = self._executar(
            "DELETE FROM solicitacoes WHERE excluido_em IS NOT NULL AND excluido_em < ?",
            (limite,),
        )
        return cur.rowcount

    # ------------------------------------------------------------------
    # Backups
    # ------------------------------------------------------------------
    def pasta_backups(self) -> str:
        """Pasta dos backups (fica dentro da pasta dos dados). É criada se preciso."""
        pasta = os.path.join(os.path.dirname(self.caminho), "backups")
        os.makedirs(pasta, exist_ok=True)
        return pasta

    def _copiar_para(self, destino: str) -> None:
        """Copia o banco de forma consistente (API de backup do SQLite) e
        troca o arquivo de destino só no fim, para nunca deixar meia-cópia."""
        provisorio = destino + ".tmp"
        if os.path.exists(provisorio):
            os.remove(provisorio)
        origem = self._conectar()
        copia = sqlite3.connect(provisorio)
        try:
            origem.backup(copia)
        finally:
            copia.close()
            origem.close()
        os.replace(provisorio, destino)

    def fazer_backup(self, nome: Optional[str] = None) -> str:
        """Cria um backup agora e aplica a rotação. Retorna o caminho do arquivo."""
        nome = nome or f"backup_{datetime.now():%Y-%m-%d_%H%M%S}.db"
        destino = os.path.join(self.pasta_backups(), nome)
        self._copiar_para(destino)
        self._aplicar_rotacao()
        return destino

    def backup_automatico(self, sobrescrever: bool = False) -> Optional[str]:
        """Backup diário (um arquivo por dia: backup_AAAA-MM-DD.db).

        Sem `sobrescrever`, só cria se ainda não houver o de hoje (uso ao abrir).
        Com `sobrescrever`, atualiza o de hoje (uso ao fechar) — mas nunca troca
        uma cópia que tem dados por uma cópia de banco vazio.
        Retorna o caminho criado, ou None se nada foi feito.
        """
        nome = f"backup_{datetime.now():%Y-%m-%d}.db"
        destino = os.path.join(self.pasta_backups(), nome)
        if os.path.exists(destino):
            if not sobrescrever or self.total_registros() == 0:
                return None
        return self.fazer_backup(nome)

    def _aplicar_rotacao(self) -> None:
        """Mantém só os backups mais recentes de cada tipo."""
        pasta = self.pasta_backups()
        for prefixo, manter in (("backup_", BACKUPS_MANTER),
                                ("antes_da_restauracao_", SEGURANCA_MANTER)):
            arquivos = []
            for nome in os.listdir(pasta):
                if nome.startswith(prefixo) and nome.endswith(".db"):
                    caminho = os.path.join(pasta, nome)
                    try:
                        arquivos.append((os.path.getmtime(caminho), nome, caminho))
                    except OSError:
                        continue
            arquivos.sort(reverse=True)
            for _mtime, _nome, caminho in arquivos[manter:]:
                try:
                    os.remove(caminho)
                except OSError:
                    pass

    @staticmethod
    def _abrir_somente_leitura(caminho: str) -> sqlite3.Connection:
        return sqlite3.connect(Path(caminho).resolve().as_uri() + "?mode=ro", uri=True)

    def _contar_em(self, caminho: str) -> Optional[int]:
        """Quantos registros (fora da lixeira) existem em um arquivo de backup."""
        try:
            conn = self._abrir_somente_leitura(caminho)
        except sqlite3.Error:
            return None
        try:
            try:
                return int(conn.execute(
                    "SELECT COUNT(*) FROM solicitacoes WHERE excluido_em IS NULL"
                ).fetchone()[0])
            except sqlite3.Error:  # backup de versão antiga (sem a coluna)
                return int(conn.execute("SELECT COUNT(*) FROM solicitacoes").fetchone()[0])
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def listar_backups(self) -> list:
        """Backups existentes, do mais recente ao mais antigo. Cada item:
        {'caminho', 'nome', 'data', 'tamanho', 'registros'}."""
        pasta = self.pasta_backups()
        itens = []
        for nome in os.listdir(pasta):
            if not nome.endswith(".db") or not nome.startswith(("backup_", "antes_da_restauracao_")):
                continue
            caminho = os.path.join(pasta, nome)
            try:
                info = os.stat(caminho)
            except OSError:
                continue
            itens.append({
                "caminho": caminho,
                "nome": nome,
                "data": datetime.fromtimestamp(info.st_mtime),
                "tamanho": info.st_size,
                "registros": self._contar_em(caminho),
            })
        itens.sort(key=lambda i: (i["data"], i["nome"]), reverse=True)
        return itens

    def _validar_backup(self, caminho: str) -> None:
        """Garante que o arquivo é um banco íntegro com a tabela esperada."""
        if not os.path.isfile(caminho):
            raise ValueError("O arquivo de backup não foi encontrado.")
        try:
            conn = self._abrir_somente_leitura(caminho)
        except sqlite3.Error:
            raise ValueError("O arquivo selecionado não é um backup válido.")
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("O backup está danificado e não pode ser restaurado.")
            colunas = {l[1] for l in conn.execute("PRAGMA table_info(solicitacoes)")}
            if not {"data_hora", "nome_paciente", "descricao", "status"} <= colunas:
                raise ValueError("O arquivo selecionado não é um backup válido.")
        except sqlite3.Error:
            raise ValueError("O arquivo selecionado não é um backup válido.")
        finally:
            conn.close()

    def restaurar_backup(self, caminho: str) -> str:
        """Substitui os dados atuais pelo conteúdo de um backup.

        Antes, guarda uma cópia de segurança do estado atual (retornada).
        Lança ValueError se o arquivo não for um backup válido (nada é alterado).
        """
        caminho = os.path.abspath(caminho)
        self._validar_backup(caminho)
        seguranca = self.fazer_backup(
            f"antes_da_restauracao_{datetime.now():%Y-%m-%d_%H%M%S}.db"
        )
        origem = self._abrir_somente_leitura(caminho)
        destino = self._conectar()
        try:
            origem.backup(destino)
        finally:
            origem.close()
            destino.close()
        self._inicializar()  # backups antigos podem não ter as colunas novas
        return seguranca
