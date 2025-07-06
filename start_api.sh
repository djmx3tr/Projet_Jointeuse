#!/bin/bash
# Script de démarrage pour l'API de Production
# À lancer au démarrage de chaque machine

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_SCRIPT="$SCRIPT_DIR/production_api.py"
LOG_FILE="$SCRIPT_DIR/api_production.log"
PID_FILE="$SCRIPT_DIR/api_production.pid"

# Fonction pour démarrer l'API
start_api() {
    echo "🚀 Démarrage de l'API de Production..."
    
    # Vérifier si l'API est déjà en cours
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "⚠️  L'API est déjà en cours d'exécution (PID: $PID)"
            return 1
        else
            echo "🧹 Suppression du fichier PID obsolète"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Activer l'environnement virtuel s'il existe
    if [ -f "$SCRIPT_DIR/../env/bin/activate" ]; then
        echo "🔧 Activation de l'environnement virtuel"
        source "$SCRIPT_DIR/../env/bin/activate"
    fi
    
    # Démarrer l'API en arrière-plan
    cd "$SCRIPT_DIR"
    nohup python3 "$API_SCRIPT" > "$LOG_FILE" 2>&1 &
    API_PID=$!
    
    # Sauvegarder le PID
    echo $API_PID > "$PID_FILE"
    
    # Attendre un peu pour vérifier que l'API démarre
    sleep 3
    
    if ps -p $API_PID > /dev/null 2>&1; then
        echo "✅ API démarrée avec succès (PID: $API_PID)"
        echo "📊 API accessible sur http://$(hostname -I | awk '{print $1}'):5001"
        echo "📝 Logs disponibles dans: $LOG_FILE"
        return 0
    else
        echo "❌ Échec du démarrage de l'API"
        echo "📝 Vérifiez les logs: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Fonction pour arrêter l'API
stop_api() {
    echo "🛑 Arrêt de l'API de Production..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "🔄 Arrêt du processus $PID"
            kill $PID
            
            # Attendre l'arrêt
            for i in {1..10}; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    echo "✅ API arrêtée avec succès"
                    rm -f "$PID_FILE"
                    return 0
                fi
                sleep 1
            done
            
            # Forcer l'arrêt si nécessaire
            echo "⚠️  Arrêt forcé du processus"
            kill -9 $PID
            rm -f "$PID_FILE"
            return 0
        else
            echo "⚠️  Le processus n'est plus actif"
            rm -f "$PID_FILE"
            return 0
        fi
    else
        echo "⚠️  Aucun fichier PID trouvé - L'API n'est probablement pas en cours"
        return 1
    fi
}

# Fonction pour vérifier le statut
status_api() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "✅ API en cours d'exécution (PID: $PID)"
            echo "📊 URL: http://$(hostname -I | awk '{print $1}'):5001"
            echo "🔍 Test: curl http://$(hostname -I | awk '{print $1}'):5001/api/health"
            return 0
        else
            echo "❌ Fichier PID trouvé mais processus inactif"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "❌ API non démarrée"
        return 1
    fi
}

# Fonction pour redémarrer l'API
restart_api() {
    echo "🔄 Redémarrage de l'API de Production..."
    stop_api
    sleep 2
    start_api
}

# Fonction pour afficher les logs
logs_api() {
    if [ -f "$LOG_FILE" ]; then
        echo "📝 Logs de l'API (dernières 50 lignes):"
        echo "----------------------------------------"
        tail -n 50 "$LOG_FILE"
    else
        echo "⚠️  Aucun fichier de log trouvé"
    fi
}

# Fonction pour tester l'API
test_api() {
    IP=$(hostname -I | awk '{print $1}')
    echo "🧪 Test de l'API sur http://$IP:5001"
    
    # Test de santé
    echo "🔍 Test /api/health..."
    if curl -s -f "http://$IP:5001/api/health" > /dev/null; then
        echo "✅ API répond correctement"
        curl -s "http://$IP:5001/api/health" | python3 -m json.tool
    else
        echo "❌ API ne répond pas"
        return 1
    fi
}

# Menu principal
case "$1" in
    start)
        start_api
        ;;
    stop)
        stop_api
        ;;
    restart)
        restart_api
        ;;
    status)
        status_api
        ;;
    logs)
        logs_api
        ;;
    test)
        test_api
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commandes disponibles:"
        echo "  start   - Démarrer l'API de production"
        echo "  stop    - Arrêter l'API de production"
        echo "  restart - Redémarrer l'API de production"
        echo "  status  - Vérifier le statut de l'API"
        echo "  logs    - Afficher les logs de l'API"
        echo "  test    - Tester l'API"
        echo ""
        echo "Exemple: $0 start"
        exit 1
        ;;
esac

exit $? 