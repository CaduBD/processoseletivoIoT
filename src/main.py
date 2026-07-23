from machine import Pin, ADC
import time

# Configuracao de hardware
btn = Pin(13, Pin.IN, Pin.PULL_UP)
ldr = ADC(Pin(32))

ldr.atten(ADC.ATTN_11DB) #Permite ler toda a faixa de 0V a ~3.3V

# Parametros de calibracao
LIMIAR_BLOQUEIO = 1500   # abaixo disso: peca bloqueando o sensor (lux baixo)
LIMIAR_LIVRE = 2500      # acima disso: linha livre (lux alto)

# Estado do sistema
contador_pecas = 0
linha_bloqueada = False

print("Peca detectada! Total: {}",(contador_pecas))

print("Contador de Producao Inicializado")

while True:
    leitura = ldr.read()

    # Borda de descida: luz caiu, peca comecou a bloquear o sensor
    if not linha_bloqueada and leitura < LIMIAR_BLOQUEIO:
        linha_bloqueada = True

    # Borda de subida: luz voltou ao normal, peca passou completamente
    elif linha_bloqueada and leitura > LIMIAR_LIVRE:
        linha_bloqueada = False
        contador_pecas += 1
        print("Peca detectada! Total: {}".format(contador_pecas))

    time.sleep_ms(10)