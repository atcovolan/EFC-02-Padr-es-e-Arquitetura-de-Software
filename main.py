import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional

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
        return int(self._data.get("interval_between_products_seconds", 5))

    def get_interval_between_cycles(self) -> int:
        return int(self._data.get("interval_between_cycles_seconds", 30))

    def get_request_headers(self) -> Dict[str, str]:
        return self._data.get("request_headers", {})


class RequestsPriceFetcher(PriceFetcher):
    """Busca o HTML usando requests (pode ser reutilizado para outros sites)."""

    def __init__(self, headers: Optional[Dict[str, str]] = None, timeout: int = 15):
        self._headers = headers or {}
        self._timeout = timeout

    def fetch_html(self, product: Product) -> str:
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
    ):
        self._products = products
        self._fetcher = fetcher
        self._parser = parser
        self._notifier = notifier
        self._interval_between_products = interval_between_products
        self._interval_between_cycles = interval_between_cycles

    def check_once(self) -> None:
        for product in self._products:
            try:
                html = self._fetcher.fetch_html(product)
                current_price = self._parser.extract_price(html)

                if current_price is None:
                    print(f"[WARN] Não foi possível extrair o preço de '{product.name}'.")
                else:
                    print(f"[INFO] {product.name} -> preço atual R$ {current_price:.2f} (target R$ {product.target_price:.2f})")

                    if current_price <= product.target_price:
                        msg = (
                            f"🔥 O preço do produto **{product.name}** caiu para "
                            f"**R$ {current_price:.2f}** (alvo: R$ {product.target_price:.2f})\n"
                            f"Link: {product.url}"
                        )
                        self._notifier.notify(msg)

            except Exception as e:
                print(f"[ERROR] Erro ao verificar {product.name}: {e}")

            # 👇 intervalo ENTRE PRODUTOS
            print(f"Aguardando {self._interval_between_products} segundos antes do próximo produto...")
            time.sleep(self._interval_between_products)

    def run_forever(self):
        while True:
            print("\n=========== VERIFICAÇÃO DE PREÇOS ===========")
            self.check_once()

            # 👇 intervalo ENTRE CICLOS
            print(f"Lista concluída. Aguardando {self._interval_between_cycles} segundos para nova verificação...\n")
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

    fetcher = RequestsPriceFetcher(headers=headers)
    parser = AmazonPriceParser()
    notifier = DiscordWebhookNotifier(webhook_url)

    monitor = PriceMonitor(
        products=products,
        fetcher=fetcher,
        parser=parser,
        notifier=notifier,
        interval_between_products=interval_between_products,
        interval_between_cycles=interval_between_cycles,
    )

    monitor.run_forever()



if __name__ == "__main__":
    main()
