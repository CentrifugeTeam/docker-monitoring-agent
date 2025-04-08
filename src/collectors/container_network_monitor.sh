#!/bin/bash

INTERVAL=5
TMP_DIR="/tmp/docker_traffic"
LOG_FILE="$TMP_DIR/current.log"
PREV_LOG_FILE="$TMP_DIR/prev.log"
STATS_FILE="$TMP_DIR/cumulative.log"

mkdir -p "$TMP_DIR"
> "$LOG_FILE"
> "$PREV_LOG_FILE"
> "$STATS_FILE"

# Получаем список IP запущенных контейнеров
get_container_ips() {
    docker ps -q | xargs -n1 docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
}

# Генерация tcpdump фильтра по IP
generate_ip_filter() {
    IPs=($(get_container_ips))
    FILTER=""
    for src in "${IPs[@]}"; do
        for dst in "${IPs[@]}"; do
            [ "$src" != "$dst" ] && FILTER+="(src $src and dst $dst) or "
        done
    done
    echo "${FILTER::-4}"  # Удалить последнюю " or "
}

# Основной цикл
while true; do
    clear
    echo "======= $(date +'%T') ======="

    # Получаем IP-фильтр
    IP_FILTER=$(generate_ip_filter)
    echo "TCPDUMP фильтр: $IP_FILTER"

    # Сбор трафика
    sudo timeout "$INTERVAL" tcpdump -i any -n -s 1500 \
        "($IP_FILTER) and (tcp or udp or icmp) and greater 128" > "$LOG_FILE" 2>/dev/null

    # Вычитаем дубликаты
    NEW_PACKETS=$(comm -13 <(sort "$PREV_LOG_FILE") <(sort "$LOG_FILE"))
    echo "$NEW_PACKETS" > "$PREV_LOG_FILE"

    # Подсчёт трафика
    declare -A traffic

    echo "$NEW_PACKETS" | awk '
    /IP / {
        split($3, src, ".");
        split($5, dst, ".");
        src_ip = src[1]"."src[2]"."src[3]"."src[4];
        dst_ip = dst[1]"."dst[2]"."dst[3]"."dst[4];

        if (index($0, "ICMP")) {
            type = "ICMP";
        } else if (index($0, "TCP")) {
            type = "TCP";
        } else if (index($0, "UDP")) {
            type = "UDP";
        } else {
            type = "OTHER";
        }

        key = src_ip" "type" "dst_ip;
        traffic[key]++;
    }
    END {
        for (k in traffic) print k, traffic[k];
    }
    ' > "$LOG_FILE.tmp"

    # Обновляем накопление
    declare -A cumulative_traffic
    while read -r line; do
        key=$(echo "$line" | cut -d' ' -f1-3)
        count=$(echo "$line" | cut -d' ' -f4)
        cumulative_traffic["$key"]=$((cumulative_traffic["$key"] + count))
    done < <(cat "$STATS_FILE" "$LOG_FILE.tmp" 2>/dev/null)

    > "$STATS_FILE"
    for key in "${!cumulative_traffic[@]}"; do
        echo "$key ${cumulative_traffic[$key]}" >> "$STATS_FILE"
    done

    # Вывод
    echo -e "\n=== Накопленная статистика трафика ==="
    printf "%-20s %-8s %-20s %-10s\n" "Источник" "Тип" "Назначение" "Пакеты"
    echo "--------------------------------------------------"
    sort "$STATS_FILE" | while read -r line; do
        src_ip=$(echo "$line" | awk '{print $1}')
        type=$(echo "$line" | awk '{print $2}')
        dst_ip=$(echo "$line" | awk '{print $3}')
        count=$(echo "$line" | awk '{print $4}')
        printf "%-20s %-8s %-20s %-10s\n" "$src_ip" "$type" "$dst_ip" "$count"
    done

    echo -e "\nСледующее обновление через $INTERVAL сек..."
    sleep 1
done
