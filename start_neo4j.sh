# Add Docker's official GPG key:
echo "Updating system packages..."
sudo apt update -y

echo "Installing Python and pip..."
sudo apt install python3 python3-pip -y

sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update


sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

tmux new-session -d -s docker-demon 
tmux send-keys -t docker-demon "dockerd" C-m 
tmux new-session -d -s docker-neo4j    
tmux send-keys -t docker-neo4j "docker run \
  --publish=7474:7474 \
  --publish=7687:7687 \
  --volume=$HOME/neo4j/data:/data \
  --name=neo4j \
  --env=NEO4J_AUTH=neo4j/password \
  neo4j" C-m 

