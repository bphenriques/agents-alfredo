"""The recipe library's format (formatting.md), shared by meals, cookidoo and drafts."""
import json
import re
import subprocess

COOK = "@cook@"

CATEGORIES = ("Pratos", "Sopas", "Sobremesas", "Pequeno-almoço", "Molhos", "Acompanhamentos", "Bases", "Bebidas", "Bebé")   # the library's folders
LEVELS = ("easy", "medium", "hard")
# One Portuguese spelling per unit, so the shopping list sums them; a plain count has none.
UNITS = {"gram": "g", "grams": "g", "gramas": "g", "dente": "dentes", "clove": "dentes", "cloves": "dentes",
         "folha": "folhas", "leaf": "folhas", "leaves": "folhas", "fatia": "fatias", "tira": "tiras", "talo": "talos",
         "pé": "pés", "ramo": "ramos", "lata": "latas", "gota": "gotas", "cubo": "cubos", "tbsp": "c. sopa", "tablespoon": "c. sopa",
         "tablespoons": "c. sopa", "c. de sopa": "c. sopa", "colher de sopa": "c. sopa", "colheres de sopa": "c. sopa",
         "tsp": "c. chá", "teaspoon": "c. chá", "teaspoons": "c. chá", "c. de chá": "c. chá", "colher de chá": "c. chá",
         "colheres de chá": "c. chá", "pinch": "pitada", "pinches": "pitada", "pitadas": "pitada", "bunch": "molho",
         "sprig": "raminhos", "sprigs": "raminhos", "raminho": "raminhos", "cup": "chávena", "cups": "chávena",
         "chávenas": "chávena", "unid.": "", "unid": "", "unidade": "", "unidades": "", "un.": ""}
PART = re.compile(r"(dentes?|folhas?|fatias?|tiras?|talos?) de (.+)")   # a count of parts, which goes in the unit


def read(path=None, text=None):
    """A recipe through cook's own parser, from a file or from text."""
    args = [COOK, "recipe", "read", "--format", "json", *([str(path)] if path else [])]
    return json.loads(subprocess.run(args, input=text, capture_output=True, text=True, check=True).stdout)


def write(path, data):
    """Replace a file whole, so a reader never sees half of it."""
    tmp = path.with_name(f".{path.name}.tmp")
    if isinstance(data, bytes):
        tmp.write_bytes(data)
    else:
        tmp.write_text(data)
    tmp.replace(path)
