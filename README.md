# haaska: Home Assistant Alexa Skill Adapter

[![Main](https://github.com/mike-grant/haaska/actions/workflows/main.yml/badge.svg)](https://github.com/mike-grant/haaska/actions/workflows/main.yml)

---

haaska implements a bridge between the [Home Assistant Smart Home API](https://www.home-assistant.io/components/alexa/#smart-home) and the [Alexa Smart Home Skill API](https://developer.amazon.com/alexa/smart-home) from Amazon.

This provides voice control for a connected home managed by Home Assistant, through any Alexa-enabled device.

### Getting Started
To get started, head over to the [haaska Wiki](https://github.com/mike-grant/haaska/wiki).

### Development

Run tests

```
python -m pytest test.py
```

### Python 3.14 ZIP build

The handler remains `haaska.event_handler` and uses the existing `config.json`
format. Copy `config/config.json.sample` to `config/config.json` and fill in
your Home Assistant URL and token before building. Certificate files can remain
in `config/`, as before.

Build with Python 3.14 and `make`, or use the Docker build environment:

```sh
docker build -t haaska-build .
docker run --rm -v "$PWD:/usr/src/app" haaska-build
```

The build always starts clean and installs the pinned runtime dependencies from
`requirements.txt`. It selects pure Python wheels so the ZIP does not contain
architecture-specific extensions. Real configuration is mounted at build time,
not copied into the Docker image. Keep the resulting ZIP private: it contains
your configured token and any client certificate keys.

To test the ZIP locally in the official Lambda Python 3.14 image, without AWS
credentials or a connection to Home Assistant:

```sh
docker run --rm --network none --entrypoint /bin/sh \
  -v "$PWD:/src:ro" public.ecr.aws/lambda/python:3.14 -c \
  'python -m zipfile -e /src/haaska.zip /tmp/package && cd /tmp/package && PYTHONPATH=/tmp/package python /src/tests/smoke_lambda.py'
```

This checks the extracted handler and dependencies against a loopback HTTP
server with fake credentials. It does not deploy or change the Lambda runtime.

### Thanks and Acknowledgement

Thanks to [@auchter](https://github.com/auchter) for creating the original haaska.

Thanks to [@bitglue](https://github.com/bitglue) for his work in getting the Smart Home API exposed via HTTP, making this slimmed down version possible.

This fork of haaska was created by [@mike-grant](https://github.com/mike-grant).

Documentation and additional maintenance is done by [@anthonylavado](https://github.com/anthonylavado), and contributors like you.

### License
haaska is provided under the [MIT License](LICENSE).
