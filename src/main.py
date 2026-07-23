from machine import Pin, ADC
import time

# Configuracao de hardware
btn = Pin(13, Pin.IN, Pin.PULL_UP)
ldr = ADC(Pin(32))

ldr.atten(ADC.ATTN_11DB) #Permite ler toda a faixa de 0V a ~3.3V

print("Contador de Producao Inicializado")


