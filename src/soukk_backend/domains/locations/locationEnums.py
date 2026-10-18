from enum import Enum


# Codes are the contract with the frontend, which maps them to Arabic/English
# labels. Never rename a code: stored locations and old app versions use it.
class District(str, Enum):
    BEIRUT = "BEIRUT"
    # Mount Lebanon
    BAABDA = "BAABDA"
    ALEY = "ALEY"
    CHOUF = "CHOUF"
    METN = "METN"
    KESERWAN = "KESERWAN"
    JBEIL = "JBEIL"
    # North
    TRIPOLI = "TRIPOLI"
    ZGHARTA = "ZGHARTA"
    KOURA = "KOURA"
    BATROUN = "BATROUN"
    BSHARRI = "BSHARRI"
    MINIYEH_DANNIYEH = "MINIYEH_DANNIYEH"
    # Akkar
    AKKAR = "AKKAR"
    # Bekaa
    ZAHLE = "ZAHLE"
    WEST_BEKAA = "WEST_BEKAA"
    RASHAYA = "RASHAYA"
    # Baalbek-Hermel
    BAALBEK = "BAALBEK"
    HERMEL = "HERMEL"
    # South
    SAIDA = "SAIDA"
    TYRE = "TYRE"
    JEZZINE = "JEZZINE"
    # Nabatieh
    NABATIEH = "NABATIEH"
    MARJEYOUN = "MARJEYOUN"
    HASBAYA = "HASBAYA"
    BINT_JBEIL = "BINT_JBEIL"


AREAS_BY_DISTRICT: dict[District, frozenset[str]] = {
    District.BEIRUT: frozenset({
        "ACHRAFIEH", "AIN_EL_MREISSEH", "BACHOURA", "HAMRA", "MAZRAA", "MEDAWAR",
        "MINET_EL_HOSN", "MOUSSAITBEH", "RAS_BEIRUT", "REMEIL", "SAIFI", "ZOKAK_EL_BLAT",
    }),
    District.BAABDA: frozenset({
        "BAABDA", "HADATH", "HAZMIEH", "CHIYAH", "GHOBEIRY", "HARET_HREIK",
        "BORJ_EL_BARAJNEH", "FURN_EL_CHEBBAK", "AIN_EL_REMMANEH",
    }),
    District.ALEY: frozenset({"ALEY", "BHAMDOUN", "SOUK_EL_GHARB", "CHOUEIFAT", "AITAT", "KHALDEH"}),
    District.CHOUF: frozenset({"BEITEDDINE", "DEIR_EL_QAMAR", "DAMOUR", "BAAKLINE", "MOUKHTARA", "JIYEH"}),
    District.METN: frozenset({
        "JDEIDEH", "SIN_EL_FIL", "DEKWANEH", "BAUCHRIEH", "ZALKA", "JAL_EL_DIB", "ANTELIAS",
        "DBAYEH", "BROUMMANA", "BEIT_MERY", "BIKFAYA", "MANSOURIEH", "BOURJ_HAMMOUD",
    }),
    District.KESERWAN: frozenset({"JOUNIEH", "ZOUK_MOSBEH", "ZOUK_MIKAEL", "KASLIK", "SARBA", "GHAZIR", "HARISSA", "FARAYA", "AJALTOUN"}),
    District.JBEIL: frozenset({"JBEIL", "AMSHIT", "BLAT", "FIDAR", "QARTABA"}),
    District.TRIPOLI: frozenset({"TRIPOLI", "MINA", "QALAMOUN"}),
    District.ZGHARTA: frozenset({"ZGHARTA", "EHDEN", "MEJDLAYA"}),
    District.KOURA: frozenset({"AMIOUN", "KOUSBA", "ENFEH"}),
    District.BATROUN: frozenset({"BATROUN", "TANNOURINE", "DOUMA", "KFARABIDA", "CHEKKA"}),
    District.BSHARRI: frozenset({"BSHARRI", "HASROUN", "BQAA_KAFRA"}),
    District.MINIYEH_DANNIYEH: frozenset({"MINIYEH", "SIR_EL_DANNIYEH", "BAKHOUN"}),
    District.AKKAR: frozenset({"HALBA", "QOBAYAT", "BIRE", "BEBNINE", "AKKAR_EL_ATIQA"}),
    District.ZAHLE: frozenset({"ZAHLE", "CHTAURA", "BAR_ELIAS", "RAYAK", "TAANAYEL", "QAB_ELIAS"}),
    District.WEST_BEKAA: frozenset({"JOUB_JANNINE", "SAGHBINE", "MACHGHARA", "QARAOUN", "KAMED_EL_LOZ"}),
    District.RASHAYA: frozenset({"RASHAYA"}),
    District.BAALBEK: frozenset({"BAALBEK", "DEIR_EL_AHMAR", "LABWEH", "ARSAL"}),
    District.HERMEL: frozenset({"HERMEL", "QASR"}),
    District.SAIDA: frozenset({"SAIDA", "MIYEH_W_MIYEH", "MAGHDOUCHEH", "GHAZIYEH", "ABRA"}),
    District.TYRE: frozenset({"TYRE", "QANA", "CHEHABIEH", "NAQOURA", "ABBASSIEH"}),
    District.JEZZINE: frozenset({"JEZZINE", "ROUM", "KFAR_FALLOUS"}),
    District.NABATIEH: frozenset({"NABATIEH", "KFAR_ROUMMAN", "DOUEIR", "HABBOUCH"}),
    District.MARJEYOUN: frozenset({"MARJEYOUN", "KHIAM", "QLEIAAH"}),
    District.HASBAYA: frozenset({"HASBAYA", "CHEBAA", "KFAR_CHOUBA"}),
    District.BINT_JBEIL: frozenset({"BINT_JBEIL", "TIBNINE", "AITA_ECH_CHAAB", "RMEICH"}),
}

# Rough bounding box of Lebanon; rejects swapped or default (0, 0) coordinates.
LATITUDE_MIN, LATITUDE_MAX = 33.05, 34.70
LONGITUDE_MIN, LONGITUDE_MAX = 35.10, 36.65
