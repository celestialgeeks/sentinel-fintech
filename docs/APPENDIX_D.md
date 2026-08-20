# APPENDIX D: DOCKER COMPOSE CONFIGURATION

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sentinel-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://sentinel:${POSTGRES_PASSWORD:-sentinel_pass}@postgres:5432/sentinel
      - REDIS_URL=redis://:${REDIS_PASSWORD:-sentinel_redis_pass}@redis:6379/0
      - MILVUS_URI=http://milvus:19530
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9093
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD:-sentinel_neo4j_pass}
      - JWT_SECRET=${JWT_SECRET:-change-this-to-a-secure-random-string}
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
      milvus: { condition: service_started }
      kafka: { condition: service_started }
      neo4j: { condition: service_healthy }
    volumes:
      - ./src:/app/src
      - ./config:/app/config
    restart: unless-stopped
    networks:
      - sentinel-net

  postgres:
    image: postgres:16-alpine
    container_name: sentinel-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=sentinel
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-sentinel_pass}
      - POSTGRES_DB=sentinel
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./config/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sentinel -d sentinel"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - sentinel-net

  redis:
    image: redis:7-alpine
    container_name: sentinel-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-sentinel_redis_pass}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-sentinel_redis_pass}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - sentinel-net

  milvus:
    image: milvusdb/milvus:v2.4.9
    container_name: sentinel-milvus
    command: ["milvus", "run", "standalone"]
    environment:
      - ETCD_ENDPOINTS=etcd:2379
      - MINIO_ADDRESS=minio:9000
      - MQ_TYPE=embedded
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    networks:
      - sentinel-net
    depends_on:
      - etcd
      - minio

  neo4j:
    image: neo4j:5.22.0
    container_name: sentinel-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-sentinel_neo4j_pass}
    volumes:
      - neo4j_data:/data
      - ./config/neo4j.conf:/var/lib/neo4j/conf/neo4j.conf
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ${NEO4J_PASSWORD:-sentinel_neo4j_pass} 'RETURN 1' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped
    networks:
      - sentinel-net

  kafka:
    image: confluentinc/cp-kafka:7.6.1
    container_name: sentinel-kafka
    ports:
      - "9092:9092"
    environment:
      - KAFKA_BROKER_ID=1
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9093,PLAINTEXT_HOST://localhost:9092
    networks:
      - sentinel-net
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.1
    container_name: sentinel-zookeeper
    environment:
      - ZOOKEEPER_CLIENT_PORT=2181
    networks:
      - sentinel-net

  prometheus:
    image: prom/prometheus:latest
    container_name: sentinel-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - sentinel-net

  grafana:
    image: grafana/grafana-oss:latest
    container_name: sentinel-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - sentinel-net
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  milvus_data:
  neo4j_data:
  prometheus_data:
  grafana_data:

networks:
  sentinel-net:
    driver: bridge
```
