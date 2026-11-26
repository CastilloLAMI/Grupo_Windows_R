"""Verifica la configuración de Docker sin necesidad de tener Docker instalado.

El job `docker` del CI construye la imagen y prueba el contenedor de verdad.
"""
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCKERFILE = RAIZ / "Dockerfile"
COMPOSE = RAIZ / "docker-compose.yml"
DOCKERIGNORE = RAIZ / ".dockerignore"
REQUISITOS_DOCKER = RAIZ / "requirements-docker.txt"


def leer(ruta):
    return ruta.read_text(encoding="utf-8")


def instrucciones(texto):
    """Líneas del Dockerfile sin comentarios ni líneas vacías."""
    return [linea.strip() for linea in texto.splitlines() if linea.strip() and not linea.strip().startswith("#")]


class TestDockerfile(unittest.TestCase):

    def setUp(self):
        self.lineas = instrucciones(leer(DOCKERFILE))
        self.texto = "\n".join(self.lineas)

    def test_imagen_base_de_python_liviana(self):
        self.assertRegex(self.lineas[0], r"^FROM python:3\.\d+-slim$")

    def test_expone_el_puerto_de_la_api(self):
        self.assertIn("EXPOSE 5000", self.lineas)

    def test_no_se_ejecuta_como_administrador(self):
        usuarios = [linea for linea in self.lineas if linea.startswith("USER ")]
        self.assertTrue(usuarios)
        self.assertNotIn(usuarios[-1], ("USER root", "USER 0"))

    def test_tiene_healthcheck_contra_salud(self):
        self.assertIn("HEALTHCHECK", self.texto)
        self.assertIn("/salud", self.texto)

    def test_arranca_la_api_con_gunicorn(self):
        ultima = self.lineas[-1]
        self.assertTrue(ultima.startswith('CMD ["gunicorn"'), ultima)
        self.assertIn("src.app:crear_app()", ultima)
        self.assertIn("GUNICORN_CMD_ARGS", self.texto)

    def test_base_de_datos_en_un_volumen(self):
        self.assertIn("EMOTI_BD=/datos/emoticontigo.db", self.texto)
        self.assertIn('VOLUME ["/datos"]', self.lineas)

    def test_copia_el_codigo_y_el_esquema(self):
        self.assertTrue(any(linea.startswith("COPY") and "src/" in linea for linea in self.lineas))
        self.assertTrue(any(linea.startswith("COPY") and "db/" in linea for linea in self.lineas))

    def test_instala_las_dependencias_antes_del_codigo(self):
        """Así Docker reutiliza la capa de dependencias al cambiar el código."""
        indice_requisitos = next(i for i, linea in enumerate(self.lineas) if "requirements-docker.txt" in linea)
        indice_codigo = next(i for i, linea in enumerate(self.lineas) if linea.startswith("COPY") and "src/" in linea)
        self.assertLess(indice_requisitos, indice_codigo)


class TestCompose(unittest.TestCase):

    def setUp(self):
        self.texto = leer(COMPOSE)

    def test_publica_el_puerto(self):
        self.assertIn('"5000:5000"', self.texto)

    def test_persiste_los_datos_y_monta_los_modelos(self):
        self.assertIn("emoti-datos:/datos", self.texto)
        self.assertIn("./modelos:/app/modelos:ro", self.texto)

    def test_construye_desde_el_dockerfile(self):
        self.assertIn("build:", self.texto)
        self.assertIn("context: .", self.texto)


class TestArchivosDeApoyo(unittest.TestCase):

    def test_dockerignore_deja_fuera_lo_pesado_y_lo_privado(self):
        excluidos = set(leer(DOCKERIGNORE).split())
        for patron in (".git", ".venv", "*.db", "modelos", "tests"):
            self.assertIn(patron, excluidos)

    def test_requisitos_de_la_imagen(self):
        texto = leer(REQUISITOS_DOCKER).lower()
        for paquete in ("flask", "gunicorn", "transformers", "pillow", "numpy"):
            self.assertIn(paquete, texto)
        self.assertNotIn("customtkinter", texto)
        self.assertNotIn("opencv", texto)


if __name__ == "__main__":
    unittest.main()
