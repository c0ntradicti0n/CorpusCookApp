import json

import requests
import config

class RequestAnnotation:
    def schedule(self,
                 command: str,
                 **kwargs):
        response = requests.post(url=f"http://localhost:{config.annotation_port}/{command}",
                      json=kwargs)

        # not 'text' for annotating, but 'text' of response is meant here:
        return json.loads(response.text)