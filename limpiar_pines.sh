#!/bin/bash
echo "limpiano pines GPIO..."
for pin in {0..27}; do
    if [ -d /sys/class/gpio/gpio$pin ]; then
        echo $pin > /sys/class/gpio/unexport
        echo "Pin $pin liberado"
    fi
done
echo "Limpieza completada"
