# Amazon Price Monitor – Projeto de Arquitetura (SOLID + Design Patterns)

Este projeto implementa um **monitor de preços da Amazon**, que verifica periodicamente o valor de produtos e envia um **alerta via Webhook do Discord** quando o preço atinge ou fica abaixo do valor desejado.

O programa foi desenvolvido seguindo os princípios **SOLID** e utilizando padrões estudados na plataforma **Refactoring.Guru**, com foco em arquitetura limpa, flexível e extensível.

---

## Funcionalidades

- Monitoramento automático de produtos da Amazon  
- Extração de preços com múltiplas estratégias  
- Retries com atraso aleatório para comportamento humano  
- Intervalo entre produtos e entre ciclos  
- Webhook do Discord para alertas  
- Configurações externas via `config.json`  
- Código estruturado usando:
  - Strategy
  - Repository
  - Dependency Injection
  - SRP, OCP, DIP (SOLID)

---

## Estrutura do Projeto

```
/src
  ├── main.py
  ├── config.json
  └── README.md
```

---

##  Como funciona

O monitor:

1. Lê produtos do `config.json`
2. Executa requisições HTTP com headers simulando um navegador
3. Extrai preço usando heurísticas (Strategy)
4. Realiza retries com atraso aleatório em caso de falha
5. Compara preço atual com o preço alvo
6. Envia notificação via Discord

Após percorrer todos os produtos, o sistema aguarda um intervalo configurado e recomeça.

---

## Código rodando

![Funcionamento](/funcionamento.png)
---

## Padrões de Projeto Utilizados

| Padrão | Onde aparece | Por quê |
|--------|--------------|--------|
| **Strategy** | `PriceParser` e `AmazonPriceParser` | Permite alterar parser sem mexer no monitor |
| **Repository** | `ConfigRepository` | Isola a leitura de configurações externas |
| **Dependency Injection** | Construtor do `PriceMonitor` | Facilita troca de componentes |
| **SOLID (SRP, OCP, DIP)** | Estrutura completa | Aumenta manutenibilidade e extensibilidade |

---
1. **Strategy**: é a interface da estratégia, AmazonPriceParser é uma implementação concreta. Se amanhã você criar KabumPriceParser, basta trocar a instância no main() sem mexer no PriceMonitor.
```python
def main():
    ...
    parser = AmazonPriceParser()   # <- estratégia concreta
    ...
    monitor = PriceMonitor(
        products=products,
        fetcher=fetcher,
        parser=parser,             # <- injetada no monitor
        ...
    )
```
2. **Repository**: ConfigRepository define o “contrato” de acesso às configurações.
JsonFileConfigRepository é o repositório concreto que sabe ler JSON.

    O resto do sistema só enxerga os métodos de alto nível (load_products(), get_webhook_url()), sem saber como isso é obtido.
```python
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
    ...
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
    ...



def main():
    config = JsonFileConfigRepository("config.json")  # <- uso do repository

    products = config.load_products()
    webhook_url = config.get_webhook_url()
    headers = config.get_request_headers()
    ...
```
3. **Dependency Injection**: PriceMonitor não instancia RequestsPriceFetcher, nem AmazonPriceParser, nem DiscordWebhookNotifier.
Ele só recebe objetos que implementam as interfaces (PriceFetcher, PriceParser, Notifier).
Isso é injeção de dependência via construtor.

```python
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
        self._fetcher = fetcher      # <- dependência injetada
        self._parser = parser        # <- dependência injetada
        self._notifier = notifier    # <- dependência injetada
        ...
```
4. **SOLID**: 
   4.1. **OCP – Open/Closed Principle**: 
```python
class KabumPriceParser(PriceParser):
    def extract_price(self, html: str) -> Optional[float]:
        ...
```
Você conseguiria adicionar essa classe sem alterar PriceMonitor. Basta trocar no main():
```python
    parser = KabumPriceParser()

```
   4.2. **DIP – Dependency Inversion Principle**: 
```python
class PriceMonitor:
    def __init__(
        ...,
        fetcher: PriceFetcher,
        parser: PriceParser,
        notifier: Notifier,
        ...
    ):
        self._fetcher = fetcher
        self._parser = parser
        self._notifier = notifier


```
PriceMonitor depende de abstrações (PriceFetcher, PriceParser, Notifier), não das classes concretas (RequestsPriceFetcher, etc.).


## Como executar

1. Instale dependências:

```bash
pip install requests beautifulsoup4
```

2. Preencha seu `config.json`

3. Execute o programa:

```bash
python main.py
```


## Como configurar um webhook no discord?

Para usar o monitor criado, você precisa de uma conta no aplicativo Discord (pode usá-lo tanto no navegador, quando programa no PC ou mesmo em sua versão mobile).

Você precisa estar em um servidor, de preferência privado, onde criará um canal de texto, e em sua configuração, criará um Webhook na parte de integrações. 

![Discord](/notifdisc.png)


## Arquivo `config.json`

Configurando o arquivo:

```json
{
  "webhook_url": "SEU_WEBHOOK",

  "interval_between_products_seconds": 20,
  "interval_between_cycles_seconds": 3600,

  "max_retries_per_product": 2,
  "retry_delay_seconds": 20,

  "request_headers": {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "pt-BR,pt;q=0.9"
  },

  "products": [
    {
      "name": "PlayStation 5 Slim",
      "url": "https://www.amazon.com.br/dp/xxxx",
      "target_price": 3200.0
    }
  ]
}
```
Aqui você coloca todos os produtos que deseja monitorar, o link do seu webhook criado no discord, o valor máximo desejado em cada um deles, o intervalo de checagem de produtos e o intervalo nas retries caso a resposta da amazon não venha com o preço.


## Exemplo de notificações

![Notificações](/notificacoes.png)

---

##  Sobre a Arquitetura

A aplicação foi projetada para ser:

- **modular**  
- **testável**  
- **pronta para expansão**

Novos sites podem ser adicionados criando novos `PriceParser`.  
Novos métodos de notificação podem ser adicionados criando novos `Notifier`.

---
