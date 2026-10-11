pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: 'github-ssh',
                    url: 'git@github.com:waniyasaeed2129/nostalgia-vault.git'
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(credentials: ['ec2-ssh']) {
                    sh '''
                    ssh -o StrictHostKeyChecking=no ubuntu@54.226.191.230 << 'EOF'
                    cd /home/ubuntu/nostalgia-vault

                    git pull origin main

                    ./venv/bin/pip install -r requirements.txt

                    sudo systemctl restart memory-vault
                    sudo systemctl restart nginx

                    echo "Deployment Successful"
                    EOF
                    '''
                }
            }
        }
    }
}
