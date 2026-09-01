from app.queues import dns_history, dns_history_apex, port_scan, ptr_sweep

# Yeni bir uzak kuyruk eklemek icin: app/queues/<isim>.py icinde ayni sekle
# sahip claim(db, max_items, token_id) / apply(db, batch_id, token, results)
# fonksiyonlarini yazip buraya ekleyin.
QUEUES = {
    "ptr_sweep": ptr_sweep,
    "dns_history": dns_history,
    "dns_history_apex": dns_history_apex,
    "port_scan": port_scan,
}
