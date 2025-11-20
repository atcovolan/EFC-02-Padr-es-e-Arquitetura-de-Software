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

## Arquivo `config.json`

Exemplo:

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

---

## Padrões de Projeto Utilizados

| Padrão | Onde aparece | Por quê |
|--------|--------------|--------|
| **Strategy** | `PriceParser` e `AmazonPriceParser` | Permite alterar parser sem mexer no monitor |
| **Repository** | `ConfigRepository` | Isola a leitura de configurações externas |
| **Dependency Injection** | Construtor do `PriceMonitor` | Facilita troca de componentes |
| **SOLID (SRP, OCP, DIP)** | Estrutura completa | Aumenta manutenibilidade e extensibilidade |

---

## Como executar

1. Instale dependências:

```bash
pip install requests beautifulsoup4
```

2. Preencha seu `config.json`

3. Execute o programa:

```bash
python price_monitor.py
```


## Como receber a notificação de preços?

Para usar o monitor criado, você precisa de uma conta no aplicativo Discord (pode usá-lo tanto no navegador, quando programa no PC ou mesmo em sua versão mobile).

Você precisa estar em um servidor, de preferência privado, onde criará um canal de texto, e em sua configuração, criará um Webhook na parte de integrações. 


---

##  Sobre a Arquitetura

A aplicação foi projetada para ser:

- **modular**  
- **testável**  
- **pronta para expansão**

Novos sites podem ser adicionados criando novos `PriceParser`.  
Novos métodos de notificação podem ser adicionados criando novos `Notifier`.

---

## 🏁 Conclusão

Projeto desenvolvido com foco em boas práticas de Arquitetura e aplicação de padrões estudados na disciplina.

