from machine import Pin, ADC
import time

# Configuracao de hardware
btn = Pin(13, Pin.IN, Pin.PULL_UP)
ldr = ADC(Pin(32))

ldr.atten(ADC.ATTN_11DB) #Permite ler toda a faixa de 0V a ~3.3V

# Parametros de calibracao
LIMIAR_BLOQUEIO = 1500   # abaixo disso: peca bloqueando o sensor (lux baixo)
LIMIAR_LIVRE = 2500      # acima disso: linha livre (lux alto)
TEMPO_MICRO_PARADA_MS = 5000 # tempo continuo bloqueado para considerar parada
DEBOUNCE_MS = 50             # tempo minimo de estabilidade para validar o botao
DEBOUNCE_LDR_MS = 50         # tempo minimo de estabilidade para validar o LDR (filtra ruido do sensor)

# Estado do sistema
contador_pecas = 0
linha_bloqueada = False
tempo_inicio_bloqueio = 0
alerta_parada_emitido = False

# Estado do LDR (debounce)
estado_ldr_bruto = None      # None = ainda indefinido (zona morta ou primeira leitura)
tempo_ultima_mudanca_ldr = time.ticks_ms()

# Estado do botao (debounce)
estado_botao_estavel = 1     # 1 = solto (pull-up), 0 = pressionado
ultima_leitura_bruta = 1
tempo_ultima_mudanca_botao = time.ticks_ms()

print("Contador de Producao Inicializado")

while True:
    leitura = ldr.read()
    agora = time.ticks_ms()

    # Debounce do LDR: so aceita mudanca de estado apos leitura estavel 
    if leitura < LIMIAR_BLOQUEIO:
        leitura_bruta_ldr = True   # bloqueado
    elif leitura > LIMIAR_LIVRE:
        leitura_bruta_ldr = False  # livre
    else:
        leitura_bruta_ldr = estado_ldr_bruto  # zona morta: mantem o que ja estava

    if leitura_bruta_ldr != estado_ldr_bruto:
        tempo_ultima_mudanca_ldr = agora
        estado_ldr_bruto = leitura_bruta_ldr

    ldr_estavel_bloqueado = (
        estado_ldr_bruto is True
        and time.ticks_diff(agora, tempo_ultima_mudanca_ldr) >= DEBOUNCE_LDR_MS
    )
    ldr_estavel_livre = (
        estado_ldr_bruto is False
        and time.ticks_diff(agora, tempo_ultima_mudanca_ldr) >= DEBOUNCE_LDR_MS
    )

    # Borda de descida: luz caiu e ficou estavel, peca comecou a bloquear o sensor
    if not linha_bloqueada and ldr_estavel_bloqueado:
        linha_bloqueada = True
        tempo_inicio_bloqueio = agora
        alerta_parada_emitido = False

    # Borda de subida: luz voltou ao normal e ficou estavel, peca passou completamente
    elif linha_bloqueada and ldr_estavel_livre:
        linha_bloqueada = False
        contador_pecas += 1
        print("Peca detectada! Total: {}".format(contador_pecas))

    # Deteccao de micro-parada: bloqueado por tempo demais sem liberar
    if linha_bloqueada and not alerta_parada_emitido:
        if time.ticks_diff(agora, tempo_inicio_bloqueio) >= TEMPO_MICRO_PARADA_MS:
            print("Alerta: Micro-parada detectada!")
            alerta_parada_emitido = True

    # Leitura do botao de reset com debounce
    leitura_bruta = btn.value()
    if leitura_bruta != ultima_leitura_bruta:
        tempo_ultima_mudanca_botao = agora
        ultima_leitura_bruta = leitura_bruta

    if time.ticks_diff(agora, tempo_ultima_mudanca_botao) >= DEBOUNCE_MS:
        if leitura_bruta != estado_botao_estavel:
            estado_botao_estavel = leitura_bruta
            if estado_botao_estavel == 0:
                contador_pecas = 0
                linha_bloqueada = False
                alerta_parada_emitido = False
                print("Turno resetado com sucesso. Contadores zerados.")


    time.sleep_ms(10) # pausa curta para nao sobrecarregar a CPU sem perder eventos rapidos
    