class MetricsFilter:
  def __init__(self):
    self.excluded_containers = [
      "k8s_POD",  # Kubernetes pause-контейнеры
      "docker-gen",  # Сервисные контейнеры
      "nginx-proxy"
    ]

  def apply(self, metrics):
    """Применяет фильтрацию к собранным метрикам"""
    filtered = metrics.copy()

    if "docker" in filtered:
      filtered["docker"] = [
        c for c in filtered["docker"]
        if not any(
          c["name"].startswith(excluded)
          for excluded in self.excluded_containers
        )
      ]

    # Дополнительная фильтрация системных метрик
    if "system" in filtered:
      if filtered["system"]["cpu"]["percent"] < 0.1:
          filtered["system"]["cpu"]["percent"] = 0.0

    return filtered
