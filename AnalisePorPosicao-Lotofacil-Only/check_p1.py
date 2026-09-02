from app import create_app
from services.analise_lotofacil_service import AnaliseLotofacilService

app = create_app()
with app.app_context():
    atrasos = AnaliseLotofacilService.calcular_atrasos_absolutos()
    p1 = atrasos['matriz_atrasos']['posicao_1']
    print("\n--- RANKING DA POSIÇÃO 1 ---")
    for i, x in enumerate(p1):
        print(f"Rank #{i+1:02d} | Dezena {x['numero']} -> Atraso {x['atraso']} concursos")
