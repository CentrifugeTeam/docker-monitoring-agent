import yaml

class Settings:
  def __init__(self, config_path="config.yml"):
    with open(config_path, 'r') as file:
      config = yaml.safe_load(file)

    self.DOCKER_SOCKET = config.get("docker_socket", "unix:///var/run/docker.sock")
    self.API_URL = config.get("api_url")
    self.TOKEN = config.get("token")
    self.INTERVAL = int(config.get("interval_seconds", 60))
    self.EXCLUDED_CONTAINERS = config.get("excluded_containers", [])

settings = Settings()
