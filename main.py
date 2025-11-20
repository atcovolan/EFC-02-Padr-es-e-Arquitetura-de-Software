import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
import random

import requests
from bs4 import BeautifulSoup


# ==========================
# Entidades de domínio
# ==========================

@dataclass
class Product:
    name: str
    url: str
    target_price: float


# ==========================
# Abstrações (Interfaces)
# ==========================

class ConfigRepository(ABC):

    @abstractmethod
    def load_products(self) -> List[Product]:
        pass

    @abstractmethod
    def get_webhook_url(self) -> str:
        pass

    @abstractmethod
    def get_request_headers(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def get_interval_between_products(self) -> int:
        pass

    @abstractmethod
    def get_interval_between_cycles(self) -> int:
        pass

    @abstractmethod
    def get_max_retries_per_product(self) -> int:
        pass

    @abstractmethod
    def get_retry_delay_seconds(self) -> int:
        pass


class PriceFetcher(ABC):

    @abstractmethod
    def fetch_html(self, product: Product) -> str:
        pass


class PriceParser(ABC):

    @abstractmethod
    def extract_price(self, html: str) -> Optional[float]:
        pass


class Notifier(ABC):

    @abstractmethod
    def notify(self, message: str) -> None:
        pass


# ==========================
# Implementações concretas
# ==========================

class JsonFileConfigRepository(ConfigRepository):
    """Lê configuração de um arquivo JSON."""

    def __init__(self, path: str):
        self._path = path
        self._data = self._load_json()

    def _load_json(self) -> dict:
        with open(self._path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_products(self) -> List[Product]:
        products_raw = self._data.get("products", [])
        products: List[Product] = []
        for p in products_raw:
            products.append(
                Product(
                    name=p["name"],
                    url=p["url"],
                    target_price=float(p["target_price"])
                )
            )
        return products

    def get_webhook_url(self) -> str:
        return self._data["webhook_url"]

    def get_interval_between_products(self) -> int:
        return int(self._data.get("interval_between_products_seconds", 30))

    def get_interval_between_cycles(self) -> int:
        return int(self._data.get("interval_between_cycles_seconds", 3600))

    def get_max_retries_per_product(self) -> int:
        return int(self._data.get("max_retries_per_product", 2))

    def get_retry_delay_seconds(self) -> int:
        return int(self._data.get("retry_delay_seconds", 30))

    def get_request_headers(self) -> Dict[str, str]:
        return self._data.get("request_headers", {})


class RequestsPriceFetcher(PriceFetcher):
    def __init__(self, headers=None, timeout=15, use_session=False):
        self._headers = headers or {}
        self._timeout = timeout
        self._use_session = use_session
        self._session = requests.Session() if use_session else None

    def fetch_html(self, product: Product) -> str:
        if self._use_session and self._session:
            resp = self._session.get(product.url, headers=self._headers, timeout=self._timeout)
        else:
            resp = requests.get(product.url, headers=self._headers, timeout=self._timeout)

        resp.raise_for_status()
        return resp.text




class AmazonPriceParser(PriceParser):
    """
    Estratégia de parsing para páginas da Amazon.

    1º tenta pegar o texto completo (R$ 1.499,99) em span.a-offscreen.
    Se não encontrar, usa os spans a-price-whole + a-price-fraction.
    """

    def extract_price(self, html: str) -> Optional[float]:
        soup = BeautifulSoup(html, "html.parser")

        # ---------- TENTATIVA 1: span.a-offscreen (funciona na maioria dos casos) ----------
        price_span = soup.select_one("span.a-offscreen")
        if not price_span:
            price_span = soup.select_one("#corePrice_feature_div span.a-offscreen")

        if price_span and price_span.get_text(strip=True):
            raw_price = price_span.get_text(strip=True)
            return self._parse_brazilian_currency(raw_price)

        # ---------- TENTATIVA 2: a-price-whole + a-price-fraction (como no print) ----------
        whole_el = soup.select_one("span.a-price-whole")
        frac_el = soup.select_one("span.a-price-fraction")

        if whole_el:
            whole_text = whole_el.get_text(strip=True)
            frac_text = frac_el.get_text(strip=True) if frac_el else "00"

            # monta algo tipo "R$ 1.499,99"
            composed_price = f"R$ {whole_text},{frac_text}"
            return self._parse_brazilian_currency(composed_price)

        # Se chegou até aqui, realmente não achou nada de preço
        print("[DEBUG] AmazonPriceParser: não encontrou nem a-offscreen nem a-price-whole.")
        return None

    @staticmethod
    def _parse_brazilian_currency(text: str) -> Optional[float]:
        """
        Converte texto como 'R$ 1.234,56' em float 1234.56.
        """
        import re

        # Mantém apenas dígitos, pontos e vírgulas
        filtered = re.sub(r"[^\d,\.]", "", text)
        if not filtered:
            return None

        # Remove separador de milhar (.) e troca vírgula por ponto
        normalized = filtered.replace(".", "").replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None


class DiscordWebhookNotifier(Notifier):
    """Envia mensagem para um webhook do Discord."""

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    def notify(self, message: str) -> None:
        payload = {"content": message}
        resp = requests.post(self._webhook_url, json=payload, timeout=10)
        resp.raise_for_status()


# ==========================
# Orquestrador (Monitor)
# ==========================

class PriceMonitor:
    def __init__(
        self,
        products: List[Product],
        fetcher: PriceFetcher,
        parser: PriceParser,
        notifier: Notifier,
        interval_between_products: int,
        interval_between_cycles: int,
        max_retries_per_product: int,
        retry_delay_seconds: int,
    ):
        self._products = products
        self._fetcher = fetcher
        self._parser = parser
        self._notifier = notifier
        self._interval_between_products = interval_between_products
        self._interval_between_cycles = interval_between_cycles
        self._max_retries_per_product = max_retries_per_product
        self._retry_delay_seconds = retry_delay_seconds

    def _random_retry_delay(self):
        import random
        base = self._retry_delay_seconds
        delay = base + random.uniform(-2, 5)
        return max(1, delay)

    def _check_single_product(self, product: Product) -> None:
        attempts = 0
        last_html = None

        while attempts <= self._max_retries_per_product:
            attempts += 1
            try:
                html = self._fetcher.fetch_html(product)
                last_html = html
                current_price = self._parser.extract_price(html)

                if current_price is not None:
                    print(
                        f"[INFO] {product.name} -> preço atual R$ {current_price:.2f} "
                        f"(target R$ {product.target_price:.2f})"
                    )

                    if current_price <= product.target_price:
                        msg = (
                            f"🔥 O preço do produto **{product.name}** caiu para "
                            f"**R$ {current_price:.2f}** (alvo: R$ {product.target_price:.2f})\n"
                            f"Link: {product.url}"
                        )
                        self._notifier.notify(msg)

                    return  # sucesso, sai do while

                print(
                    f"[WARN] Tentativa {attempts} não conseguiu extrair o preço de '{product.name}'."
                )

            except Exception as e:
                print(f"[ERROR] Erro na tentativa {attempts} para {product.name}: {e}")

            if attempts <= self._max_retries_per_product:
                delay = self._random_retry_delay()
                print(f"Aguardando {delay:.2f} segundos para tentar novamente...")
                time.sleep(delay)

        # se chegou aqui, falhou todas as tentativas
        print(f"[ERROR] Falha definitiva ao extrair preço de '{product.name}'.")
        if last_html:
            with open("last_failed.html", "w", encoding="utf-8") as f:
                f.write(last_html)
            print("[DEBUG] HTML da última tentativa salvo em last_failed.html")

    def check_once(self) -> None:
        for idx, product in enumerate(self._products, start=1):
            print(f"\n--- Produto {idx}: {product.name} ---")
            self._check_single_product(product)

            if idx < len(self._products):
                print(
                    f"Aguardando {self._interval_between_products} segundos "
                    f"antes de verificar o próximo produto..."
                )
                time.sleep(self._interval_between_products)

    def run_forever(self) -> None:
        while True:
            print("\n=========== INICIANDO CICLO DE VERIFICAÇÃO ===========")
            self.check_once()
            print(
                f"\nCiclo finalizado. Aguardando {self._interval_between_cycles} segundos "
                f"para iniciar um novo ciclo...\n"
            )
            time.sleep(self._interval_between_cycles)




# ==========================
# Ponto de entrada
# ==========================

def main():
    config = JsonFileConfigRepository("config.json")

    products = config.load_products()
    webhook_url = config.get_webhook_url()
    headers = config.get_request_headers()

    interval_between_products = config.get_interval_between_products()
    interval_between_cycles = config.get_interval_between_cycles()
    max_retries = config.get_max_retries_per_product()
    retry_delay = config.get_retry_delay_seconds()

    fetcher = RequestsPriceFetcher(headers=headers)
    parser = AmazonPriceParser()   # sua versão original
    notifier = DiscordWebhookNotifier(webhook_url)

    monitor = PriceMonitor(
        products=products,
        fetcher=fetcher,
        parser=parser,
        notifier=notifier,
        interval_between_products=interval_between_products,
        interval_between_cycles=interval_between_cycles,
        max_retries_per_product=max_retries,
        retry_delay_seconds=retry_delay,
    )

    monitor.run_forever()




if __name__ == "__main__":
    main()
