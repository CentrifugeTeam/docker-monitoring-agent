import gzip
import json
import base64

class GzipCompressor:
  def compress(self, data):
      """Сжимает данные и возвращает base64 строку"""
      if isinstance(data, dict):
          data = json.dumps(data)
      if isinstance(data, str):
          data = data.encode('utf-8')

      compressed = gzip.compress(data)
      return base64.b64encode(compressed).decode('utf-8')
