"""Registro reducido de skills HTTP de JARVIS-LITE."""

from .abstract_email_skill import skill_abstract_email
from .abstract_phone_skill import skill_abstract_phone
from .abstract_ip_skill import skill_abstract_ip
from .aviation_skill import skill_info_vuelo
from .countrylayer_skill import skill_info_pais
from .calendar_skill import agregar_evento, ver_eventos
from .cocktail_skill import skill_cocktail_by_ingredient, skill_cocktail_random, skill_cocktail_search
from .dietly_skill import skill_dietly
from .extra_api_skills import (
    skill_biblia,
    skill_buscar_web,
    skill_cotizacion,
    skill_geocodificar,
    skill_hibp,
    skill_securitytrails,
)
from .football_skill import skill_football_ligas
from .fun_fact_skill import skill_fun_fact
from .geoapify_skill import skill_geoapify_ip, skill_geoapify_reverse
from .gmail_skill import leer_correos
from .image_gen_skill import skill_editar_imagen, skill_generar_imagen
from .ip_geolocation_skill import skill_geoip
from .ipapi_skill import skill_geoip_ipapi
from .ipstack_skill import skill_geoip_ipstack
from .lempi_skill import usar_lempi
from .mailboxlayer_skill import skill_validar_email
from .meal_skill import skill_meal_by_category, skill_meal_random, skill_meal_search
from .mobileapi_skill import skill_buscar_celular
from .numlookup_skill import skill_validar_telefono_numlookup
from .numverify_skill import skill_validar_telefono
from .news_skill import consultar_noticias
from .osint_skill import skill_osint_domain, skill_osint_email, skill_osint_username
from .orshot_skill import skill_generar_imagen_orshot
from .postali_skill import skill_postali
from .recipeapi_skill import skill_recipeapi
from .sheets_skill import registrar_gasto
from .spotify_skill import buscar_y_reproducir, controlar_spotify
from .tasty_skill import skill_tasty_recipes
from .veriphone_skill import skill_validar_telefono_veriphone
from .weather_skill import consultar_calidad_aire, consultar_clima, consultar_pronostico
from .weatherstack_skill import skill_clima_weatherstack
from .usertack_skill import skill_track_usuario
from .video_ai_skill import skill_generar_video

SKILLS = {
    "clima": consultar_clima,
    "pronostico": consultar_pronostico,
    "calidad_aire": consultar_calidad_aire,
    "vuelo": skill_info_vuelo,
    "clima_weatherstack": skill_clima_weatherstack,
    "noticias": consultar_noticias,
    "buscar_web": skill_buscar_web,
    "biblia": skill_biblia,
    "cotizacion": skill_cotizacion,
    "geocodificar": skill_geocodificar,
    "hibp": skill_hibp,
    "securitytrails": skill_securitytrails,
    "info_pais": skill_info_pais,
    "geoip": skill_geoip,
    "geoip_ipstack": skill_geoip_ipstack,
    "geoip_ipapi": skill_geoip_ipapi,
    "geoapify_ip": skill_geoapify_ip,
    "geoapify_reverse": skill_geoapify_reverse,
    "track_usuario": skill_track_usuario,
    "telefono_abstract": skill_abstract_phone,
    "telefono_numlookup": skill_validar_telefono_numlookup,
    "telefono_numverify": skill_validar_telefono,
    "telefono_veriphone": skill_validar_telefono_veriphone,
    "email_abstract": skill_abstract_email,
    "email_mailboxlayer": skill_validar_email,
    "ip_abstract": skill_abstract_ip,
    "osint_email": skill_osint_email,
    "osint_domain": skill_osint_domain,
    "osint_username": skill_osint_username,
    "buscar_celular": skill_buscar_celular,
    "postal": skill_postali,
    "futbol": skill_football_ligas,
    "receta": skill_recipeapi,
    "dietly": skill_dietly,
    "tasty": skill_tasty_recipes,
    "comida": skill_meal_search,
    "comida_random": skill_meal_random,
    "coctel": skill_cocktail_search,
    "coctel_random": skill_cocktail_random,
    "coctel_ingrediente": skill_cocktail_by_ingredient,
    "dato_curioso": skill_fun_fact,
    "imagen": skill_generar_imagen,
    "imagen_orshot": skill_generar_imagen_orshot,
    "editar_imagen": skill_editar_imagen,
    "lempi": usar_lempi,
    "video": skill_generar_video,
    "spotify_buscar": buscar_y_reproducir,
    "spotify_control": controlar_spotify,
    "eventos": ver_eventos,
    "agregar_evento": agregar_evento,
    "correos": leer_correos,
    "gasto": registrar_gasto,
}
