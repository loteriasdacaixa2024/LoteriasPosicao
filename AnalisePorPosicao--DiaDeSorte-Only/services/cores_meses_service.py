import json
import os

class CoresMesesService:
    @staticmethod
    def _get_json_path():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, 'config_meses.json')

    @staticmethod
    def obter_cores():
        json_path = CoresMesesService._get_json_path()
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                "Janeiro": "#e74c3c", "Fevereiro": "#9b59b6", "Março": "#3498db",
                "Abril": "#e67e22", "Maio": "#f1c40f", "Junho": "#2ecc71",
                "Julho": "#1abc9c", "Agosto": "#34495e", "Setembro": "#196f3d",
                "Outubro": "#d35400", "Novembro": "#8e44ad", "Dezembro": "#c0392b"
            }

    @staticmethod
    def salvar_cores(novas_cores):
        json_path = CoresMesesService._get_json_path()
        try:
            # Mantém as cores antigas caso alguma falte no dict novo
            cores_atuais = CoresMesesService.obter_cores()
            cores_atuais.update(novas_cores)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cores_atuais, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Erro ao salvar cores: {e}")
            return False

    @staticmethod
    def gerar_css():
        cores = CoresMesesService.obter_cores()
        css_lines = []
        for mes, cor in cores.items():
            css_lines.append(f".mes-nome-{mes} {{ background-color: {cor} !important; color: #fff !important; }}")
            css_lines.append(f".mes-text-{mes} {{ color: {cor} !important; }}")
            css_lines.append(f".mes-border-{mes} {{ border-color: {cor} !important; }}")
        
        return "\n".join(css_lines)
