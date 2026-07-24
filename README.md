# Contador de Produção Não-Intrusivo 

## Identificação do Candidato

- **Nome completo:** Carlos Eduardo Batista Diniz
- **GitHub:** [@CaduBD](https://github.com/CaduBD)

## Visão Geral da Solução

Este projeto implementa um **Contador de Produção Não-Intrusivo**, uma solução de baixo custo voltada para indústrias e linhas de montagem que operam sem CLPs, eliminando a necessidade de anotações manuais e fornecendo métricas de produtividade em tempo real.

O sistema utiliza um sensor óptico baseado em fotorresistor (LDR) posicionado ao longo de uma esteira transportadora. Quando uma peça interrompe o feixe de luz incidente sobre o sensor, o firmware detecta essa obstrução e, assim que a peça termina de passar (o feixe é restabelecido), registra o evento e incrementa o contador de produção. Em paralelo, o sistema monitora continuamente o tempo em que a linha permanece bloqueada: se esse tempo ultrapassar um limite configurado, entende-se que há uma micro-parada (gargalo) na esteira, e um alerta é emitido. Um botão físico de reset permite ao operador encerrar e zerar o turno de trabalho atual a qualquer momento.

A interação com o sistema ocorre inteiramente via **Monitor Serial** (para leitura dos eventos: contagem de peças, alertas de parada e confirmações de reset) e por um **botão físico**, sem necessidade de interface gráfica adicional — refletindo o caráter de baixo custo e simplicidade de instalação que o projeto se propõe a ter.

## Arquitetura do Sistema Embarcado

O firmware é estruturado em um único laço principal (`while True`), executado de forma **totalmente não-bloqueante**. Isso significa que, a cada iteração do loop, o sistema lê o estado atual do sensor e do botão, atualiza sua máquina de estados interna e segue adiante — sem nunca "parar" a execução esperando algum evento externo, o que garante responsividade constante aos estímulos do ambiente simulado.

### Fluxo principal (`main.py`)

1. **Inicialização:**
   - Configuração do pino do LDR como entrada analógica (ADC), com atenuação ajustada para ler toda a faixa de tensão de 0 a ~3.3V
   - Configuração do pino do botão como entrada digital com resistor de pull-up interno
   - Impressão da mensagem de status inicial via Serial

2. **Loop principal**, executado continuamente a cada ~10ms:
   - **Leitura do LDR:** a leitura bruta do ADC é comparada contra dois limiares (`LIMIAR_LIVRE` e `LIMIAR_BLOQUEIO`), classificando o estado do sensor como "livre", "bloqueado" ou mantendo o estado anterior (zona morta)
   - **Debounce do LDR:** a mudança de estado só é aceita como válida após permanecer estável por um tempo mínimo, filtrando ruído
   - **Máquina de estados da linha:** ao detectar uma transição estável de "livre" para "bloqueado", marca o início do bloqueio e reinicia o alerta de parada; ao detectar a transição inversa (peça passou completamente), incrementa o contador de peças e imprime o log correspondente
   - **Verificação de micro-parada:** enquanto a linha permanece bloqueada, o tempo decorrido é comparado ao limite configurado; se ultrapassado, o alerta é emitido uma única vez (controlado por uma flag), evitando repetição desnecessária enquanto a mesma parada persiste
   - **Leitura do botão com debounce:** de forma similar ao LDR, a leitura do botão só é considerada válida após estabilização; ao detectar a transição de "pressionado" para "solto" (liberação do botão), o sistema executa o reset completo do turno (zera contador, desbloqueia a linha e reinicia a flag de alerta)

### Diagrama do fluxo principal

```
[Boot] → Configura pinos (LDR/ADC, Botao/pull-up) → Imprime status inicial
                                    │
                                    ▼
                          ┌───────────────────┐
                          │   Loop principal   │◄─────────────┐
                          │   (while True)     │               │
                          └─────────┬──────────┘               │
                                    │                           │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  Le LDR + debounce          Verifica micro-parada        Le botao + debounce
        │                     (se linha bloqueada)                │
        ▼                           │                             ▼
  Atualiza estado da        Emite alerta (1x) se          Se transicao para
  linha (livre/bloqueada)   tempo >= limite                "solto": reseta
        │                                                  contadores e estado
        ▼
  Se peca passou:
  incrementa contador
  e imprime log
        │
        └─────────────► sleep_ms(10) ─────────────────────────────┘
```

### Estrutura de estados

O sistema é modelado com as seguintes variáveis de estado centrais:

| Variável | Tipo | Função |
|---|---|---|
| `linha_bloqueada` | bool | Indica se a linha está atualmente obstruída por uma peça |
| `alerta_parada_emitido` | bool | Evita disparos repetidos do alerta enquanto a mesma parada persiste |
| `estado_ldr_bruto` / `estado_botao_estavel` | bool/int | Guardam o último estado "confirmado" (pós-debounce) de cada entrada |
| `contador_pecas` | int | Contador de peças detectadas no turno atual |

### Temporização não-bloqueante

Toda a lógica de tempo (debounce, detecção de micro-parada) utiliza `time.ticks_ms()` combinado com `time.ticks_diff()`, em vez de subtração direta entre timestamps. Isso é intencional: o contador interno de milissegundos do MicroPython tem tamanho limitado e eventualmente sofre *overflow* (reinicia do zero); `ticks_diff()` trata esse caso corretamente, calculando a diferença real de tempo mesmo quando esse "estouro" ocorre — algo que uma subtração ingênua não faria.

## Componentes Utilizados na Simulação

| Componente | ID (`diagram.json`) | Pino de Conexão | Função no Sistema |
|---|---|---|---|
| ESP32 DevKit C v4 | `esp` | — | Microcontrolador principal, executa o firmware MicroPython |
| Fotorresistor (LDR) | `ldr1` | `AO → GPIO32` (ADC) | Detecta variações de luminosidade para identificar a passagem de peças |
| Botão (Pushbutton) | `btn1` | `GPIO13` (pull-up interno) | Reset manual do turno de produção |
| Monitor Serial | — | `TX/RX` | Exibição dos logs de eventos do sistema em tempo real |

## Decisões Técnicas Relevantes

- **Histerese na leitura do LDR:** em vez de um único valor de corte, foram definidos dois limiares distintos, com uma "zona morta" entre eles. Essa técnica (amplamente usada em sensores analógicos e termostatos, por exemplo) evita que pequenas oscilações de leitura, decorrentes de ruído do sensor, causem transições de estado falsas e, consequentemente, contagens ou alertas incorretos.

- **Debounce aplicado tanto ao botão quanto ao LDR:** inicialmente, apenas o botão possuía debounce (prática padrão para entradas mecânicas). Durante os testes automatizados, identificou-se que o próprio LDR simulado também apresentava variações momentâneas de leitura, gerando um alerta de micro-parada falso mesmo com a linha permanecendo "livre". A solução foi aplicar o mesmo princípio de debounce à leitura do sensor analógico, exigindo estabilidade mínima antes de aceitar uma transição de estado.

- **Calibração empírica da escala do sensor:** a suposição inicial era de que uma leitura de ADC mais alta corresponderia a maior luminosidade. Ao testar o circuito simulado, os dados coletados mostraram o comportamento oposto: `832 lux → ADC ≈ 756` (leitura baixa) e `50 lux → ADC ≈ 2531` (leitura alta) — uma relação inversamente proporcional, decorrente da posição do LDR no divisor de tensão da montagem. A lógica de comparação dos limiares foi então recalibrada com base nesses valores reais medidos, em vez de manter uma suposição não verificada.

- **Reset disparado na liberação do botão, não na pressão:** originalmente, o reset era acionado assim que o botão era pressionado. Isso causava falha no cenário de teste automatizado, pois a mensagem de confirmação era emitida antes do mecanismo de verificação (`wait-serial`) do framework de testes estar pronto para capturá-la — mesmo a mensagem aparecendo corretamente no log da simulação, o teste expirava por timeout. Alterar o disparo para o momento da liberação do botão alinhou o comportamento do firmware ao timing esperado pelo cenário de teste, sem alterar a lógica funcional do sistema.

- **Ausência de funções bloqueantes longas:** a única pausa no loop principal é `time.sleep_ms(10)`, entre uma leitura e outra. Esse valor foi escolhido por ser significativamente menor que o menor intervalo relevante entre eventos nos cenários de teste (200ms), garantindo múltiplas leituras dentro de qualquer janela de estímulo, sem comprometer a responsividade do sistema.

## Resultados Obtidos

Os três cenários de teste automatizados (Wokwi CI, executados via GitHub Actions a cada push) foram validados com sucesso:

- ✅ **Cenário 1 — Contagem Normal de Peças:** o sistema detecta corretamente a obstrução e liberação do sensor, incrementando o contador e emitindo `Peca detectada! Total: X` no momento correto.
- ✅ **Cenário 2 — Detecção de Micro-parada:** ao manter a linha bloqueada continuamente além do limite configurado (5 segundos), o sistema emite `Alerta: Micro-parada detectada!` exatamente uma vez.
- ✅ **Cenário 3 — Reset Manual de Turno:** ao pressionar e soltar o botão, o sistema zera os contadores e emite `Turno resetado com sucesso. Contadores zerados.`, sincronizado corretamente com o mecanismo de verificação do teste.

Todos os testes passam de forma consistente e reprodutível na pipeline de CI, sem uso de funções bloqueantes que comprometam a sincronia com os estímulos programados nos cenários.

## Comentários Adicionais

### Dificuldades encontradas

O maior desafio deste projeto não esteve na lógica de máquina de estados em si — que é relativamente direta — mas na **calibração e depuração do comportamento real do hardware simulado**. Duas descobertas, em particular, exigiram investigação baseada em evidências em vez de suposições:

1. A relação entre luminosidade e leitura do ADC não seguiu o padrão inicialmente esperado, e só foi corretamente identificada após imprimir a leitura bruta do sensor sob diferentes condições de luz e comparar com os valores exatos de `lux` utilizados nos cenários de teste.

2. O comportamento do mecanismo `wait-serial` do Wokwi CI — que só captura mensagens emitidas *após* o listener estar ativo — não é evidente apenas lendo a documentação, e só foi identificado ao comparar cenários que passavam (onde havia um `delay` suficiente antes da mensagem) com o que falhava por timeout mesmo exibindo o texto esperado corretamente no log.

3. Um erro de configuração no workflow (nome do secret esperado pela action, `WOKWI_CLI_TOKEN`, diferente do nome sugerido inicialmente no README, `WOKWI_API_KEY`) também precisou ser identificado através da leitura cuidadosa dos logs de execução do GitHub Actions.

### Limitações da solução

Os limiares de luminosidade (`LIMIAR_LIVRE`, `LIMIAR_BLOQUEIO`) e os tempos de debounce foram calibrados com base nos valores específicos observados na simulação atual. Em um cenário de instalação real (ou mesmo em uma simulação com iluminação ambiente diferente), esses valores fixos poderiam não ser adequados, exigindo recalibração manual do código.

### Melhorias que faria com mais tempo

- Implementar uma rotina de **calibração automática** na inicialização do sistema, medindo o valor de "linha livre" real do ambiente nos primeiros segundos de operação, em vez de depender de constantes fixas no código.
- Tornar os parâmetros de temporização (tempo de micro-parada, debounce) configuráveis externamente, sem necessidade de alterar o firmware.
- Adicionar testes unitários isolados para a lógica de máquina de estados, permitindo validar o comportamento sem depender exclusivamente da simulação completa no Wokwi.

### Principais aprendizados durante o desafio

- A importância de **validar hipóteses técnicas com dados reais** em vez de assumir comportamentos "padrão" de componentes eletrônicos — a relação entre luminosidade e leitura do ADC só ficou clara após medição direta, não por dedução teórica.
- Entendimento prático de **histerese e debounce** como técnicas fundamentais para lidar com ruído em sensores analógicos e entradas digitais, evitando falsos positivos em sistemas de contagem e controle.
- A relevância de entender o **funcionamento interno das ferramentas de teste automatizado** (como o `wait-serial` do Wokwi CI) — nem sempre a mensagem "aparecer certa" no log é suficiente; o *timing* de quando ela é emitida em relação ao ciclo de vida do teste também importa.
- Reforço da prática de **depuração incremental e baseada em evidências**: em vez de tentar corrigir múltiplos problemas simultaneamente, isolar cada falha (analisando logs do CI, comparando cenários que passavam com os que falhavam) permitiu identificar a causa raiz de forma mais eficiente do que tentativa e erro às cegas.