import LCD_I2C_classe as LCD
import time as time
lcd = LCD.LCD_I2C()

lcd.write("hello world",1)
time.sleep(5)

lcd.clear()
