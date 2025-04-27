# Используем образ Ubuntu
FROM ubuntu:latest

# Устанавливаем SSH сервер
RUN apt-get update && apt-get install -y openssh-server sudo && rm -rf /var/lib/apt/lists/*

# Создаем пользователя sftpuser
RUN useradd -m -d /home/sftpuser -s /bin/bash sftpuser && echo "sftpuser:sftppassword" | chpasswd

# Создаем директорию для загрузки файлов
RUN mkdir -p /home/sftpuser/uploads && chmod 777 /home/sftpuser/uploads

# Копируем конфигурацию SSH
COPY sshd_config /etc/ssh/sshd_config

# Открываем порт для SSH (по умолчанию это порт 22)
EXPOSE 22

# Запускаем SSH сервер
CMD ["/usr/sbin/sshd", "-D"]
