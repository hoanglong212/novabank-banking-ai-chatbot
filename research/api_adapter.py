"""Research-only Chat Completions transport. Disabled until explicitly enabled.

No SDK/dependency additions, import-time network, automatic retries or raw logging.
`python -m research.api_adapter` only checks configuration; it cannot call a model.
"""
import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import httpx
from dotenv import dotenv_values


class ApiDisabled(RuntimeError):
    pass


class ApiAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    supports_seed: bool = False

    @classmethod
    def from_env(cls, env_file=None):
        path = Path(env_file) if env_file else Path(__file__).resolve().parents[1] / '.env'
        values = dotenv_values(path, interpolate=False) if path.is_file() else {}
        def value(key, default=''):
            return os.environ.get(key, values.get(key) or default)
        return cls(base_url=value('RESEARCH_API_BASE_URL'), model=value('RESEARCH_API_MODEL', '<API_MODEL>'),
                   api_key=value('RESEARCH_API_KEY'), supports_seed=value('RESEARCH_API_SUPPORTS_SEED', 'false').lower() == 'true')

    def validate(self):
        url = urlsplit(self.base_url)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('API base URL must be HTTPS without credentials, query or fragment')
        if not self.model.strip() or '<' in self.model or '>' in self.model:
            raise ValueError('Choose an approved immutable API model snapshot first')
        if not self.api_key.strip() or '<' in self.api_key or any(c.isspace() for c in self.api_key):
            raise ValueError('A valid API key must be supplied privately through environment configuration')


class ApiAdapter:
    def __init__(self, config, *, client=None, allow_live=False):
        self.config = config
        self.client = client
        self.allow_live = allow_live

    def complete(self, messages, tools=None, *, seed=None, max_tokens=512):
        if not self.allow_live:
            raise ApiDisabled('API transport is disabled; explicit approval and enablement required')
        self.config.validate()
        body = {'model': self.config.model, 'messages': messages, 'stream': False,
                'temperature': 0, 'max_completion_tokens': max_tokens}
        if tools:
            body['tools'] = tools
        sent_seed = seed if self.config.supports_seed else None
        if sent_seed is not None:
            body['seed'] = sent_seed
        started = time.perf_counter()
        owned = self.client is None
        client = self.client or httpx.Client(timeout=120, follow_redirects=False, trust_env=False)
        try:
            response = client.post(self.config.base_url.rstrip('/') + '/chat/completions', json=body,
                                   headers={'Authorization': 'Bearer ' + self.config.api_key}, follow_redirects=False)
            if response.status_code != 200:
                raise ApiAdapterError(f'API returned HTTP {response.status_code}; response body withheld')
            data = response.json()
            usage = data['usage']
            counts = [usage['prompt_tokens'], usage['completion_tokens']]
            if any(type(n) is not int or n < 0 for n in counts):
                raise ValueError('Invalid usage')
            choice = data['choices'][0]
            message = choice['message']
            calls = []
            for call in message.get('tool_calls') or []:
                fn = call['function']
                args = json.loads(fn['arguments']) if isinstance(fn['arguments'], str) else fn['arguments']
                if not isinstance(args, dict) or not isinstance(fn['name'], str):
                    raise ValueError('Invalid tool call')
                calls.append({'id': call.get('id'), 'function': {'name': fn['name'], 'arguments': args}})
            content = message.get('content') or ''
            if not isinstance(content, str):
                raise ValueError('Invalid content')
            return {'message': {'content': content, 'tool_calls': calls},
                    'input_tokens': counts[0], 'output_tokens': counts[1],
                    'latency_ms': round((time.perf_counter() - started) * 1000),
                    'model_requested': self.config.model, 'model_returned': data['model'],
                    'response_id': data.get('id'), 'system_fingerprint': data.get('system_fingerprint'),
                    'finish_reason': choice.get('finish_reason'), 'seed_requested': seed, 'seed_sent': sent_seed}
        except ApiAdapterError as exc:
            raise ApiAdapterError(str(exc)) from None
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            raise ApiAdapterError('API transport or response validation failed; details withheld') from None
        finally:
            if owned:
                client.close()


def main():
    parser = argparse.ArgumentParser(description='Offline configuration check; no model calls')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    cfg = ApiConfig.from_env(args.env_file)
    try:
        cfg.validate()
        valid = True
    except ValueError:
        valid = False
    print(json.dumps({'configuration_valid': valid, 'key_present': bool(cfg.api_key),
                      'transport_enabled': False, 'network_calls': 0}))


if __name__ == '__main__':
    main()
