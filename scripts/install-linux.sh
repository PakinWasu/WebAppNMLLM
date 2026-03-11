#!/bin/bash
# WebAppNMLLM Linux Installation Script
# สคริปต์ติดตั้งอัตโนมัติสำหรับ Linux/Ubuntu

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "ไม่ควรรันสคริปต์นี้ด้วย root user"
        print_warning "กรุณารันด้วย user ทั่วไปที่มี sudo privileges"
        exit 1
    fi
}

# Function to detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        print_error "ไม่สามารถตรวจสอบระบบปฏิบัติการได้"
        exit 1
    fi
    
    print_status "ตรวจพบระบบ: $OS $VER"
}

# Function to check system requirements
check_requirements() {
    print_status "ตรวจสอบความต้องการของระบบ..."
    
    # Check RAM
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    if [[ $TOTAL_RAM -lt 8 ]]; then
        print_warning "RAM น้อยกว่า 8GB อาจทำให้ระบบทำงานช้า"
        read -p "ต้องการดำเนินการต่อหรือไม่? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    if [[ $CPU_CORES -lt 4 ]]; then
        print_warning "CPU cores น้อยกว่า 4 อาจทำให้ LLM ทำงานช้า"
    fi
    
    # Check disk space
    DISK_SPACE=$(df . | tail -1 | awk '{print $4}')
    if [[ $DISK_SPACE -lt 20971520 ]]; then # 20GB in KB
        print_error "พื้นที่ว่างน้อยกว่า 20GB"
        exit 1
    fi
    
    print_success "ผ่านการตรวจสอบความต้องการของระบบ"
}

# Function to install Docker
install_docker() {
    if command -v docker &> /dev/null; then
        print_success "Docker ติดตั้งแล้ว"
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_status "Docker version: $DOCKER_VERSION"
    else
        print_status "กำลังติดตั้ง Docker..."
        
        # Update package index
        sudo apt-get update
        
        # Install packages to allow apt to use a repository over HTTPS
        sudo apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
        
        # Add Docker's official GPG key
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        
        # Set up the stable repository
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
            $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker Engine
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Add user to docker group
        sudo usermod -aG docker $USER
        
        print_success "ติดตั้ง Docker เสร็จสิ้น"
        print_warning "กรุณา logout และ login ใหม่เพื่อใช้งาน Docker โดยไม่ต้อง sudo"
    fi
}

# Function to check Docker Compose
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_VERSION=$(docker-compose --version)
        print_status "Docker Compose: $DOCKER_COMPOSE_VERSION"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE_VERSION=$(docker compose version)
        print_status "Docker Compose (plugin): $DOCKER_COMPOSE_VERSION"
    else
        print_error "Docker Compose ไม่พบ"
        exit 1
    fi
}

# Function to create directories
create_directories() {
    print_status "สร้าง directories ที่จำเป็น..."
    
    mkdir -p storage
    mkdir -p mongo-data
    mkdir -p mongo-backup
    
    # Set permissions
    chmod -R 777 storage/
    chmod -R 755 mongo-data/
    chmod -R 755 mongo-backup/
    
    print_success "สร้าง directories เสร็จสิ้น"
}

# Function to generate JWT secret
generate_jwt_secret() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        # Fallback method
        LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 64
    fi
}

# Function to create .env file
create_env_file() {
    ENV_FILE="backend/.env"
    
    if [[ -f $ENV_FILE ]]; then
        print_warning "พบไฟล์ $ENV_FILE แล้ว"
        read -p "ต้องการสร้างใหม่หรือไม่? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    print_status "สร้างไฟล์คอนฟิก .env..."
    
    # Get user input
    echo
    print_status "=== การตั้งค่า MongoDB ==="
    read -p "MongoDB URI [mongodb://mongodb:27017]: " MONGODB_URI
    MONGODB_URI=${MONGODB_URI:-mongodb://mongodb:27017}
    
    read -p "MongoDB Database Name [manage_network_projects]: " MONGODB_DB_NAME
    MONGODB_DB_NAME=${MONGODB_DB_NAME:-manage_network_projects}
    
    echo
    print_status "=== การตั้งค่า JWT Security ==="
    JWT_SECRET=$(generate_jwt_secret)
    read -p "JWT Secret (กด Enter เพื่อสร้างอัตโนมัติ): " USER_JWT_SECRET
    if [[ -z $USER_JWT_SECRET ]]; then
        JWT_SECRET=$JWT_SECRET
        print_success "สร้าง JWT Secret อัตโนมัติ"
    else
        JWT_SECRET=$USER_JWT_SECRET
    fi
    
    echo
    print_status "=== การตั้งค่า Ollama LLM ==="
    read -p "Ollama Base URL [http://ollama:11434]: " OLLAMA_BASE_URL
    OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://ollama:11434}
    
    read -p "Ollama Model [qwen2.5:7b]: " OLLAMA_MODEL
    OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
    
    read -p "Use LLM for Topology Generation? [Y/n]: " TOPOLOGY_USE_LLM
    TOPOLOGY_USE_LLM=${TOPOLOGY_USE_LLM:-y}
    if [[ $TOPOLOGY_USE_LLM =~ ^[Yy]$ ]]; then
        TOPOLOGY_USE_LLM=true
    else
        TOPOLOGY_USE_LLM=false
    fi
    
    echo
    print_status "=== การตั้งค่า Resource ==="
    read -p "Memory Limit for Ollama (GB) [20]: " OLLAMA_MEMORY
    OLLAMA_MEMORY=${OLLAMA_MEMORY:-20}
    
    read -p "CPU Cores for Ollama [4]: " OLLAMA_CPUS
    OLLAMA_CPUS=${OLLAMA_CPUS:-4}
    
    # Create .env file
    cat > $ENV_FILE << EOF
# MongoDB Configuration
MONGODB_URI=$MONGODB_URI
MONGODB_DB_NAME=$MONGODB_DB_NAME

# JWT Security Configuration
JWT_SECRET=$JWT_SECRET
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MIN=1440

# Ollama Configuration
OLLAMA_BASE_URL=$OLLAMA_BASE_URL
OLLAMA_MODEL=$OLLAMA_MODEL
OLLAMA_TIMEOUT=600

# Topology: use LLM for topology generation
TOPOLOGY_USE_LLM=$TOPOLOGY_USE_LLM

# Resource settings (reflected in docker-compose.prod.yml)
# Memory: ${OLLAMA_MEMORY}GB, CPU: ${OLLAMA_CPUS} cores
EOF
    
    print_success "สร้างไฟล์ $ENV_FILE เสร็จสิ้น"
}

# Function to update docker-compose with resource settings
update_docker_compose() {
    print_status "อัปเดต docker-compose.prod.yml ด้วยค่า resource..."
    
    # Read resource values from .env
    source backend/.env 2>/dev/null || true
    
    # Default values if not set
    OLLAMA_MEMORY=${OLLAMA_MEMORY:-20}
    OLLAMA_CPUS=${OLLAMA_CPUS:-4}
    
    # Update docker-compose.prod.yml
    sed -i "s/memory: [0-9]*G/memory: ${OLLAMA_MEMORY}G/" docker-compose.prod.yml
    sed -i "s/cpus: '[0-9]*'/cpus: '${OLLAMA_CPUS}'/" docker-compose.prod.yml
    
    print_success "อัปเดต docker-compose.prod.yml เสร็จสิ้น"
}

# Function to pull and start services
start_services() {
    print_status "ดาวน์โหลด Docker images..."
    docker compose -f docker-compose.prod.yml pull
    
    print_status "สร้างและสตาร์ท containers..."
    docker compose -f docker-compose.prod.yml up -d --build
    
    print_status "รอสักครู่ให้ services start ทั้งหมด..."
    sleep 30
}

# Function to download LLM model
download_llm_model() {
    print_status "ดาวน์โหลด LLM model..."
    
    # Read model from .env
    source backend/.env
    OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
    
    print_status "กำลังดาวน์โหลดโมเดล: $OLLAMA_MODEL"
    print_warning "นี่อาจใช้เวลานานขึ้นอยู่กับขนาดโมเดลและความเร็วอินเทอร์เน็ต"
    
    # Download model
    if docker compose -f docker-compose.prod.yml exec -T ollama ollama pull $OLLAMA_MODEL; then
        print_success "ดาวน์โหลดโมเดล $OLLAMA_MODEL เสร็จสิ้น"
    else
        print_error "ไม่สามารถดาวน์โหลดโมเดลได้"
        print_warning "คุณสามารถดาวน์โหลดภายหลังด้วย: docker compose -f docker-compose.prod.yml exec ollama ollama pull $OLLAMA_MODEL"
    fi
}

# Function to verify installation
verify_installation() {
    print_status "ตรวจสอบการติดตั้ง..."
    
    # Check containers
    echo
    print_status "สถานะ containers:"
    docker compose -f docker-compose.prod.yml ps
    
    # Check services health
    echo
    print_status "ตรวจสอบสถานะ services..."
    
    # Check backend
    if curl -s http://localhost:8001/ > /dev/null; then
        print_success "Backend API พร้อมใช้งาน: http://localhost:8001"
    else
        print_warning "Backend API อาจยังไม่พร้อมใช้งาน"
    fi
    
    # Check frontend
    if curl -s http://localhost:8080/ > /dev/null; then
        print_success "Frontend พร้อมใช้งาน: http://localhost:8080"
    else
        print_warning "Frontend อาจยังไม่พร้อมใช้งาน"
    fi
    
    # Check Ollama
    if docker compose -f docker-compose.prod.yml exec -T ollama ollama list > /dev/null 2>&1; then
        print_success "Ollama พร้อมใช้งาน: http://localhost:11434"
    else
        print_warning "Ollama อาจยังไม่พร้อมใช้งาน"
    fi
}

# Function to show final instructions
show_instructions() {
    echo
    echo "=========================================="
    print_success "การติดตั้ง WebAppNMLLM เสร็จสิ้น!"
    echo "=========================================="
    echo
    print_status "การเข้าใช้งานระบบ:"
    echo "  Frontend: http://localhost:8080"
    echo "  Backend API: http://localhost:8001"
    echo "  API Docs: http://localhost:8001/docs"
    echo
    print_status "การเข้าสู่ระบบครั้งแรก:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo
    print_warning "สำคัญ: เปลี่ยนรหัสผ่านทันทีหลัง login ครั้งแรก!"
    echo
    print_status "คำสั่งที่ใช้บ่อย:"
    echo "  ดูสถานะ: docker compose -f docker-compose.prod.yml ps"
    echo "  ดู logs: docker compose -f docker-compose.prod.yml logs -f"
    echo "  Restart: ./scripts/update-and-restart.sh"
    echo "  Stop: docker compose -f docker-compose.prod.yml down"
    echo
    print_status "ไฟล์คอนฟิกหลัก:"
    echo "  Backend config: backend/.env"
    echo "  Docker config: docker-compose.prod.yml"
    echo
    echo "=========================================="
}

# Main installation flow
main() {
    echo "=========================================="
    echo "  WebAppNMLLM Linux Installation Script"
    echo "=========================================="
    echo
    
    check_root
    detect_os
    check_requirements
    
    echo
    read -p "ต้องการดำเนินการติดตั้งหรือไม่? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "ยกเลิกการติดตั้ง"
        exit 0
    fi
    
    install_docker
    check_docker_compose
    create_directories
    create_env_file
    update_docker_compose
    start_services
    download_llm_model
    verify_installation
    show_instructions
}

# Run main function
main "$@"
