{ config, pkgs, lib, ... }:

let
  appDir = "/srv/tickettgbot";
  appUser = "tickettgbot";
  serverIP = "1.2.3.4";  # замініть на ваш IP
in
{
  users.users.${appUser} = {
    isSystemUser = true;
    group = appUser;
    home = appDir;
  };
  users.groups.${appUser} = {};

  services.mysql = {
    enable = true;
    package = pkgs.mysql80;
    ensureDatabases = [ "ticketbot" ];
    ensureUsers = [{
      name = appUser;
      ensurePermissions."ticketbot.*" = "ALL PRIVILEGES";
    }];
  };

  # Nginx із самопідписаним сертифікатом на IP
  # Спочатку згенеруйте сертифікат (дивіться нижче)
  services.nginx = {
    enable = true;
    recommendedProxySettings = true;

    virtualHosts."${serverIP}" = {
      addSSL = true;
      sslCertificate = "/etc/ssl/tickettgbot/cert.pem";
      sslCertificateKey = "/etc/ssl/tickettgbot/key.pem";

      locations."/" = {
        proxyPass = "http://127.0.0.1:8000";
        extraConfig = ''
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-Proto https;
          proxy_read_timeout 60s;
        '';
      };
    };
  };

  networking.firewall.allowedTCPPorts = [ 80 443 ];

  # Сервіс FastAPI (для Mini App)
  systemd.services.tickettgbot-api = {
    description = "TicketTgBot FastAPI";
    after = [ "network.target" "mysql.service" ];
    wants = [ "mysql.service" ];
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      User = appUser;
      Group = appUser;
      WorkingDirectory = appDir;
      ExecStart = "${appDir}/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000";
      EnvironmentFile = "${appDir}/.env";
      Restart = "on-failure";
      RestartSec = "5s";
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ appDir ];
      PrivateTmp = true;
    };
  };

  # Сервіс бота в polling-режимі (якщо без webhook)
  systemd.services.tickettgbot-bot = {
    description = "TicketTgBot Polling";
    after = [ "network.target" "mysql.service" "tickettgbot-api.service" ];
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      User = appUser;
      Group = appUser;
      WorkingDirectory = appDir;
      ExecStart = "${appDir}/.venv/bin/python run_polling.py";
      EnvironmentFile = "${appDir}/.env";
      Restart = "on-failure";
      RestartSec = "5s";
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ appDir ];
      PrivateTmp = true;
    };
  };
}
