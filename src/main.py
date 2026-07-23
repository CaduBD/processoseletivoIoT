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

# Estado do sistema
contador_pecas = 0
linha_bloqueada = False
tempo_inicio_bloqueio = 0
alerta_parada_emitido = False

print("Contador de Producao Inicializado")

while True:
    leitura = ldr.read()
    agora = time.ticks_ms()

    # Borda de descida: luz caiu, peca comecou a bloquear o sensor
    if not linha_bloqueada and leitura < LIMIAR_BLOQUEIO:
        linha_bloqueada = True
        tempo_inicio_bloqueio = agora
        alerta_parada_emitido = False

    # Borda de subida: luz voltou ao normal, peca passou completamente
    elif linha_bloqueada and leitura > LIMIAR_LIVRE:
        linha_bloqueada = False
        contador_pecas += 1
        print("Peca detectada! Total: {}".format(contador_pecas))

    # Deteccao de micro-parada: bloqueado por tempo demais sem liberar
    if linha_bloqueada and not alerta_parada_emitido:
        if time.ticks_diff(agora, tempo_inicio_bloqueio) >= TEMPO_MICRO_PARADA_MS:
            print("Alerta: Micro-parada detectada!")
            alerta_parada_emitido = True

    time.sleep_ms(10)
    