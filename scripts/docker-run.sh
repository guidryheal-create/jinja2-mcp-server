#!/bin/bash

# Jinja2 MCP Server Docker 启动脚本
# 支持多种部署模式

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
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

# 显示帮助信息
show_help() {
    echo "Jinja2 MCP Server Docker 部署脚本"
    echo ""
    echo "用法: $0 [模式] [选项]"
    echo ""
    echo "部署模式:"
    echo "  stdio     启动stdio模式 (默认，适合AI客户端)"
    echo "  http      启动HTTP模式 (适合调试和测试)"
    echo "  dev       启动开发模式 (支持代码热重载)"
    echo "  build     仅构建Docker镜像"
    echo "  stop      停止所有容器"
    echo "  clean     清理所有容器和镜像"
    echo ""
    echo "选项:"
    echo "  -p, --port PORT    指定HTTP端口 (默认: 8123)"
    echo "  -d, --detach       后台运行"
    echo "  -h, --help         显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 http              # 启动HTTP模式"
    echo "  $0 http -p 9000      # 启动HTTP模式，使用端口9000"
    echo "  $0 stdio -d          # 后台启动stdio模式"
    echo "  $0 dev               # 启动开发模式"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
}

# 构建Docker镜像
build_image() {
    print_info "构建Docker镜像..."
    docker-compose build --no-cache
    print_success "Docker镜像构建完成"
}

# 启动stdio模式
start_stdio() {
    print_info "启动Jinja2 MCP Server (stdio模式)..."
    
    if [ "$DETACH" = true ]; then
        docker-compose --profile stdio up -d
    else
        docker-compose --profile stdio up
    fi
    
    print_success "Jinja2 MCP Server (stdio模式) 已启动"
}

# 启动HTTP模式
start_http() {
    print_info "启动Jinja2 MCP Server (HTTP模式) 在端口 $PORT..."
    
    # 设置端口环境变量
    export MCP_PORT=$PORT
    
    if [ "$DETACH" = true ]; then
        docker-compose --profile http up -d
    else
        docker-compose --profile http up
    fi
    
    print_success "Jinja2 MCP Server (HTTP模式) 已启动"
    print_info "访问地址: http://localhost:$PORT"
    print_info "健康检查: http://localhost:$PORT/health"
}

# 启动开发模式
start_dev() {
    print_info "启动Jinja2 MCP Server (开发模式) 在端口 $PORT..."
    
    # 设置端口环境变量
    export MCP_PORT=$PORT
    
    if [ "$DETACH" = true ]; then
        docker-compose --profile dev up -d
    else
        docker-compose --profile dev up
    fi
    
    print_success "Jinja2 MCP Server (开发模式) 已启动"
    print_info "访问地址: http://localhost:$PORT"
    print_warning "开发模式已启用代码热重载"
}

# 停止所有容器
stop_containers() {
    print_info "停止所有Jinja2 MCP Server容器..."
    docker-compose --profile stdio --profile http --profile dev down
    print_success "所有容器已停止"
}

# 清理容器和镜像
clean_all() {
    print_warning "这将删除所有Jinja2 MCP Server相关的容器、镜像和卷"
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "清理容器和镜像..."
        docker-compose --profile stdio --profile http --profile dev down -v --rmi all
        print_success "清理完成"
    else
        print_info "操作已取消"
    fi
}

# 默认值
MODE=""
PORT=8123
DETACH=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        stdio|http|dev|build|stop|clean)
            MODE="$1"
            shift
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--detach)
            DETACH=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 如果没有指定模式，默认为stdio
if [ -z "$MODE" ]; then
    MODE="stdio"
fi

# 检查Docker环境
check_docker

# 根据模式执行相应操作
case $MODE in
    build)
        build_image
        ;;
    stdio)
        build_image
        start_stdio
        ;;
    http)
        build_image
        start_http
        ;;
    dev)
        build_image
        start_dev
        ;;
    stop)
        stop_containers
        ;;
    clean)
        clean_all
        ;;
    *)
        print_error "无效的模式: $MODE"
        show_help
        exit 1
        ;;
esac 