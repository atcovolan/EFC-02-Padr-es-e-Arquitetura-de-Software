# 1. Estudo Teórico dos Padrões de Projeto

Este documento apresenta os padrões de projeto aplicados no desenvolvimento do **Amazon Price Monitor**, seguindo o conteúdo de estudo da plataforma *Refactoring.Guru*.

Padrões utilizados:

- Strategy  
- Repository  
- Dependency Injection  
- Princípios SOLID  

---

## Padrão Strategy

### Definição Teórica  

O padrão Strategy encapsula diferentes algoritmos dentro de uma interface comum.  
Cada implementação representa uma estratégia que pode ser trocada sem alterar o funcionamento da aplicação.

### Quando usar  

- Quando existem várias formas de executar a mesma ação  
- Quando o algoritmo pode mudar ao longo do tempo  
- Para evitar condicionais extensas (`if/else`) no código principal  


### Por que foi escolhido  

Porque o HTML da Amazon muda com frequência e o monitor precisa ser capaz de usar diferentes formas de parsing, além de permitir que no futuro o mesmo monitor funcione com outros sites apenas trocando a estratégia de parsing.

---

## Padrão Repository

### Definição Teórica  

Repository atua como uma camada intermediária entre a aplicação e a fonte de dados (arquivo, banco de dados, API, etc.), expondo métodos de alto nível e escondendo detalhes de leitura, parsing e estrutura dos dados.

### Quando usar  

- Quando queremos separar a lógica de leitura de dados da lógica de negócio  
- Quando a origem dos dados pode mudar (arquivo → API, por exemplo)  
- Quando precisamos facilitar testes unitários



### Por que foi escolhido  

Porque o monitor não deve ter conhecimento de como os dados estão armazenados fisicamente.  
O padrão permite trocar o JSON por API, banco de dados, YAML, etc., sem alterar o monitor.

---

## Padrão Dependency Injection (DI)

### Definição Teórica  

As dependências são fornecidas externamente, ao invés de criadas dentro da classe.

### Usos principais  

- Reduz acoplamento  
- Facilita testes (substituição por mocks)
- Permite trocar componentes sem alterar o código principal  

###  Por que foi escolhido  

Porque permite que o monitor seja totalmente genérico, dependendo apenas de **interfaces**, e não de implementações concretas.

---

# 2. Estudo Teórico dos Princípios SOLID

---

##  S — Single Responsibility Principle  

Cada classe possui **uma única responsabilidade**.

##  O — Open/Closed Principle  

Aberto para extensão, fechado para modificação.

##  L — Liskov Substitution Principle  

Subclasses devem substituir suas classes base sem quebrar o sistema.

##  I — Interface Segregation Principle  

Preferir interfaces pequenas e específicas.

##  D — Dependency Inversion Principle  

Depender de abstrações, não de implementações.

---

# 3. Justificativas Detalhadas de Cada Padrão

---

# Strategy — Justificativa

###  Por que foi escolhido  

O HTML da Amazon muda, e o Strategy permite trocar o algoritmo de extração sem alterar o restante do sistema.

###  Problema que resolve  

Evita acoplamento entre o monitor e o mecanismo de parsing.

###  Benefícios  

- Extensível  
- Testável  
- Modular  

###  Como seria sem o padrão  

Um monte de `if/else` dentro do monitor.

---

#  Repository — Justificativa

###  Por que foi escolhido  

Para isolar completamente a lógica de leitura da configuração.

###  Problema que resolve  

Remove do monitor a responsabilidade de ler JSON e interpretar dados.

###  Benefícios  

- Testes mais simples  
- Extensível  
- Baixo acoplamento  

---

#  Dependency Injection — Justificativa

###  Por que foi escolhido  

Para permitir que o monitor dependa de abstrações, e não de classes concretas.

###  Benefícios  

- Substituição simples de módulos  
- Testes com mocks  
- Extensibilidade total  

---

#  4. SOLID Aplicado

- SRP: cada classe tem um único motivo para mudar  
- OCP: adicionar funcionalidades não exige modificar o monitor  
- LSP: qualquer implementação substitui sua interface  
- ISP: interfaces pequenas e específicas  
- DIP: monitor depende de abstrações  

---
