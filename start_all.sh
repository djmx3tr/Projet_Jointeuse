#!/bin/bash
# Script de démarrage COMPLET pour Raspberry Pi
# Démarre l'interface utilisateur ET l'API en une seule commande

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERFACE_SCRIPT="$SCRIPT_DIR/interface_graphique_production_v2.py"
API_SCRIPT="$SCRIPT_DIR/production_api.py"
LOG_DIR="$SCRIPT_DIR/logs"
INTERFACE_LOG="$LOG_DIR/interface.log"
API_LOG="$LOG_DIR/api.log"
INTERFACE_PID="$SCRIPT_DIR/interface.pid"
API_PID="$SCRIPT_DIR/api.pid"

# Créer le dossier de logs
mkdir -p "$LOG_DIR"

# Fonction pour démarrer tout
start_all() {
    echo "🚀 Démarrage complet de la machine jointeuse..."
    echo "📍 Machine: $(hostname)"
    echo "🌐 IP: $(hostname -I | awk '{print $1}')"
    echo ""
    
    # Vérifier si déjà en cours
    if [ -f "$INTERFACE_PID" ] && [ -f "$API_PID" ]; then
        IPID=$(cat "$INTERFACE_PID" 2>/dev/null)
        APID=$(cat "$API_PID" 2>/dev/null)
        if ps -p $IPID > /dev/null 2>&1 && ps -p $APID > /dev/null 2>&1; then
            echo "⚠️  Système déjà en cours d'exécution"
            echo "   Interface PID: $IPID"
            echo "   API PID: $APID"
            return 1
        fi
    fi
    
    # Définir le chemin Python avec environnement virtuel
    if [ -f "$SCRIPT_DIR/../env/bin/python" ]; then
        echo "🔧 Utilisation de l'environnement virtuel..."
        PYTHON_CMD="$SCRIPT_DIR/../env/bin/python"
    else
        echo "⚠️  Environnement virtuel non trouvé, utilisation de python3"
        PYTHON_CMD="python3"
    fi
    
    cd "$SCRIPT_DIR"
    
    # 1. Démarrer l'interface utilisateur
    echo "🖥️  Démarrage de l'interface utilisateur..."
    nohup "$PYTHON_CMD" "$INTERFACE_SCRIPT" > "$INTERFACE_LOG" 2>&1 &
    INTERFACE_PID_NUM=$!
    echo $INTERFACE_PID_NUM > "$INTERFACE_PID"
    
    # Attendre un peu
    sleep 3
    
    # Vérifier que l'interface a démarré
    if ps -p $INTERFACE_PID_NUM > /dev/null 2>&1; then
        echo "✅ Interface utilisateur démarrée (PID: $INTERFACE_PID_NUM)"
    else
        echo "❌ Échec démarrage interface"
        return 1
    fi
    
    # 2. Démarrer l'API
    echo "📡 Démarrage de l'API de production..."
    nohup "$PYTHON_CMD" "$API_SCRIPT" > "$API_LOG" 2>&1 &
    API_PID_NUM=$!
    echo $API_PID_NUM > "$API_PID"
    
    # Attendre un peu
    sleep 3
    
    # Vérifier que l'API a démarré
    if ps -p $API_PID_NUM > /dev/null 2>&1; then
        echo "✅ API de production démarrée (PID: $API_PID_NUM)"
    else
        echo "❌ Échec démarrage API"
        return 1
    fi
    
    echo ""
    echo "🎉 SYSTÈME COMPLET DÉMARRÉ !"
    echo "┌─────────────────────────────────────┐"
    echo "│ 🖥️  Interface locale : Écran machine │"
    echo "│ 📡 API partagée : Port 5001         │"
    echo "│ 🌐 URL API : http://$(hostname -I | awk '{print $1}'):5001 │"
    echo "└─────────────────────────────────────┘"
    echo ""
    echo "📝 Logs disponibles dans: $LOG_DIR/"
    echo "🔍 Vérifier statut: $0 status"
}

# Fonction pour arrêter tout
stop_all() {
    echo "🛑 Arrêt complet du système..."
    
    # Arrêter l'interface
    if [ -f "$INTERFACE_PID" ]; then
        IPID=$(cat "$INTERFACE_PID")
        if ps -p $IPID > /dev/null 2>&1; then
            echo "🖥️  Arrêt de l'interface utilisateur..."
            kill $IPID
            rm -f "$INTERFACE_PID"
        fi
    fi
    
    # Arrêter l'API
    if [ -f "$API_PID" ]; then
        APID=$(cat "$API_PID")
        if ps -p $APID > /dev/null 2>&1; then
            echo "📡 Arrêt de l'API..."
            kill $APID
            rm -f "$API_PID"
        fi
    fi
    
    # Attendre l'arrêt
    sleep 2
    
    echo "✅ Système arrêté"
}

# Fonction pour vérifier le statut
status_all() {
    echo "📊 Statut du système:"
    echo ""
    
    # Statut interface
    if [ -f "$INTERFACE_PID" ]; then
        IPID=$(cat "$INTERFACE_PID")
        if ps -p $IPID > /dev/null 2>&1; then
            echo "🖥️  Interface utilisateur : ✅ EN COURS (PID: $IPID)"
        else
            echo "🖥️  Interface utilisateur : ❌ ARRÊTÉE"
            rm -f "$INTERFACE_PID"
        fi
    else
        echo "🖥️  Interface utilisateur : ❌ NON DÉMARRÉE"
    fi
    
    # Statut API
    if [ -f "$API_PID" ]; then
        APID=$(cat "$API_PID")
        if ps -p $APID > /dev/null 2>&1; then
            echo "📡 API de production : ✅ EN COURS (PID: $APID)"
            echo "🌐 URL : http://$(hostname -I | awk '{print $1}'):5001"
        else
            echo "📡 API de production : ❌ ARRÊTÉE"
            rm -f "$API_PID"
        fi
    else
        echo "📡 API de production : ❌ NON DÉMARRÉE"
    fi
    
    echo ""
    echo "💻 Machine: $(hostname)"
    echo "🌐 IP: $(hostname -I | awk '{print $1}')"
}

# Fonction pour redémarrer
restart_all() {
    echo "🔄 Redémarrage complet du système..."
    stop_all
    sleep 3
    start_all
}

# Fonction pour afficher les logs
logs_all() {
    echo "📝 Logs du système:"
    echo ""
    
    if [ -f "$INTERFACE_LOG" ]; then
        echo "🖥️  INTERFACE (dernières 20 lignes):"
        echo "────────────────────────────────────"
        tail -n 20 "$INTERFACE_LOG"
        echo ""
    fi
    
    if [ -f "$API_LOG" ]; then
        echo "📡 API (dernières 20 lignes):"
        echo "────────────────────────────────────"
        tail -n 20 "$API_LOG"
    fi
}

# Fonction pour tester l'API
test_api() {
    IP=$(hostname -I | awk '{print $1}')
    echo "🧪 Test de l'API sur http://$IP:5001"
    
    if curl -s -f "http://$IP:5001/api/health" > /dev/null; then
        echo "✅ API répond correctement"
        curl -s "http://$IP:5001/api/health" | python -m json.tool
    else
        echo "❌ API ne répond pas"
        return 1
    fi
}

# Menu principal
case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status_all
        ;;
    logs)
        logs_all
        ;;
    test)
        test_api
        ;;
    *)
        echo "🏭 Script de démarrage COMPLET - Machine Jointeuse"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commandes disponibles:"
        echo "  start   - 🚀 Démarrer TOUT (Interface + API)"
        echo "  stop    - 🛑 Arrêter TOUT"
        echo "  restart - 🔄 Redémarrer TOUT"
        echo "  status  - 📊 Vérifier le statut"
        echo "  logs    - 📝 Afficher les logs"
        echo "  test    - 🧪 Tester l'API"
        echo ""
        echo "⭐ COMMANDE PRINCIPALE: $0 start"
        echo ""
        exit 1
        ;;
esac

exit $? 