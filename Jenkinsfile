pipeline {
  agent {
    node {
      label "simulator-any"
    }
  }

  post {
    failure {
      updateGitlabCommitStatus name: 'build', state: 'failed'
    }
    success {
      updateGitlabCommitStatus name: 'build', state: 'success'
    }
  }

  options {
    gitLabConnection("${GITLAB_HOST}")
    skipDefaultCheckout(true)
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timestamps()
  }

  parameters {
    string(name: 'BRANCH_NAME', defaultValue: 'master', description: 'Branch from HDRP/Scenarios/runner to build', trim: true)
    string(name: 'GIT_TAG', defaultValue: '', description: 'Tag from HDRP/Scenarios/runner to build as a release (will be pushed with version__<tag>_<build-number> docker tag)', trim: true)
    string(name: 'WISE_AWS_ECR_ACCOUNT_ID', defaultValue: '853285614468', description: 'The AWS account ID whose ECR will be used', trim: true)
    string(name: 'WISE_AWS_ECR_REGION', defaultValue: 'us-east-1', description: 'The AWS region where the ECR is located', trim: true)
    credentials( name: 'WISE_AWS_ECR_CREDENTIALS_ID', required: true, defaultValue: "simulator--aws-credentials", description: 'The credentials to be used for accessing the ECR', credentialType: 'com.cloudbees.jenkins.plugins.awscredentials.AWSCredentialsImpl')
  }

  environment {
    PYTHONUNBUFFERED = "1"
    JENKINS_BUILD_ID = "${BUILD_ID}"
    DOCKER_TAG = "build__${JENKINS_BUILD_ID}"
    GIT_VER = "${sh(script:'[ -n "${GIT_TAG}" ] && echo "refs/tags/${GIT_TAG}" || echo "refs/heads/${BRANCH_NAME}"', returnStdout: true).trim()}"
    GITLAB_REPO_PYTHON = "hdrp/scenarios/runner/python"
    GITLAB_REPO_VSE = "hdrp/scenarios/runner/vse"
    ECR_REPO_PYTHON = "wise/runner/python"
    ECR_REPO_VSE = "wise/runner/vse"
    DOCKER_REPO_SUFFIX = "${sh(script:'[ "${BRANCH_NAME}" != "master" ] && /bin/echo -n "/" && echo "${BRANCH_NAME}" | tr / -  | tr [:upper:] [:lower:] || true', returnStdout: true).trim()}"
    GIT_TAG_FOR_DOCKER = "${sh(script:'echo "${GIT_TAG}" | tr / -  | tr [:upper:] [:lower:]', returnStdout: true).trim()}"
  }

  stages {
    stage("NotifyGitlab") {
      steps {
        updateGitlabCommitStatus name: 'build', state: 'running'
      }
    }
    stage("Git") {
      steps {
        checkout([
          $class: "GitSCM",
          branches: [[name: "${GIT_VER}"]],
          browser: [$class: "GitLab", repoUrl: "https://${GITLAB_HOST}/HDRP/Scenarios/runner", version: env.GITLAB_VERSION],
          doGenerateSubmoduleConfigurations: false,
          extensions: [
            [$class: "GitLFSPull"],
            [$class: 'SubmoduleOption',
            disableSubmodules: false,
            parentCredentials: true,
            recursiveSubmodules: true,
            reference: '',
            trackingSubmodules: false]
          ],
          userRemoteConfigs: [[
            credentialsId: "auto-gitlab",
            url: "git@${GITLAB_HOST}:HDRP/Scenarios/runner.git"
          ]]
        ])
      }
    }

    stage("DockerLogin") {
      environment {
        DOCKERHUB_DOCKER_REGISTRY = credentials("dockerhub-docker-registry")
        AUTO_GITLAB_DOCKER_REGISTRY = credentials("auto-gitlab-docker-registry")
      }
      steps {
        dir("Jenkins") {
          sh """
            docker login -u "${DOCKERHUB_DOCKER_REGISTRY_USR}" -p "${DOCKERHUB_DOCKER_REGISTRY_PSW}"
            docker login -u "${AUTO_GITLAB_DOCKER_REGISTRY_USR}" -p "${AUTO_GITLAB_DOCKER_REGISTRY_PSW}" ${GITLAB_HOST}:4567
          """
        }
      }
    }

    stage("build") {
      steps {
        sh """
          docker build -f docker/Dockerfile.python \
                       --pull \
                       --no-cache \
                       --build-arg PYTHON_INSTALL_ENV='SCENARIO_RUNNER__BUILD_KIND=official' \
                       --build-arg image_git_describe="\$(git describe --always --tags --match 20*)" \
                       --build-arg image_git_describe_submodules="\$(git submodule | xargs)" \
                       --build-arg image_tag=\$DOCKER_TAG \
                       --build-arg image_uuidgen=\$(uuidgen) \
                       -t ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                       .

          docker push ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG

          if [ -n "${env.GIT_TAG_FOR_DOCKER}" ]; then
              docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                          ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
              docker push ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
          fi

          docker build -f docker/Dockerfile.vse \
                       --pull \
                       --no-cache \
                       --build-arg PYTHON_INSTALL_ENV='SCENARIO_RUNNER__BUILD_KIND=official' \
                       --build-arg image_git_describe="\$(git describe --always --tags --match 20*)" \
                       --build-arg image_git_describe_submodules="\$(git submodule | xargs)" \
                       --build-arg image_tag=\$DOCKER_TAG \
                       --build-arg image_uuidgen=\$(uuidgen) \
                       -t ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                       .

          docker push ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG

          if [ -n "${env.GIT_TAG_FOR_DOCKER}" ]; then
              docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                          ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
              docker push ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
          fi
        """
      }
    }

    stage("push latest") {
      when {
        anyOf {
          branch 'master'
        }
      }
      steps {
        sh script:"""
          docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                      ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:latest

          docker push ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:latest
          """, label:"${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:latest"

        sh script:"""
          docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                      ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:latest

          docker push ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:latest
          """, label:"${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:latest"
      }
    }

    stage("uploadECR") {
      steps {
          sh "echo Using credentials ${WISE_AWS_ECR_CREDENTIALS_ID}"
          withCredentials([[credentialsId: "${WISE_AWS_ECR_CREDENTIALS_ID}", accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', $class: 'AmazonWebServicesCredentialsBinding']]) {
            sh """
              DOCKER_REGISTRY="${WISE_AWS_ECR_ACCOUNT_ID}.dkr.ecr.${WISE_AWS_ECR_REGION}.amazonaws.com"
              # According to https://hub.docker.com/r/amazon/aws-cli, the version tags are immutable => no need to force pulling.
              AWSCLI="amazon/aws-cli:2.2.20"

              if ! docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY --rm -t \$AWSCLI ecr get-login-password --region $WISE_AWS_ECR_REGION | docker login --username AWS --password-stdin \$DOCKER_REGISTRY; then
                echo "ABORT: bad AWS credentials?"
                exit 1
              fi

              # Push GITLAB_REPO_PYTHON
              if ! docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY --rm -t \$AWSCLI ecr create-repository --repository-name \$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX --region $WISE_AWS_ECR_REGION; then
                echo "INFO: aws-cli ecr create-repository --repository-name \$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX --region $WISE_AWS_ECR_REGION failed - assuming that it's because the repo already exists in ECR"
              fi
              docker tag ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \$DOCKER_REGISTRY/\$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
              docker push \$DOCKER_REGISTRY/\$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
              if [ -z "${env.GIT_TAG_FOR_DOCKER}" ]; then
                  docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                              \$DOCKER_REGISTRY/\$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
                  docker push \$DOCKER_REGISTRY/\$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
                  docker image rm \$DOCKER_REGISTRY/\$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
              fi

              docker image rm \
                  ${GITLAB_HOST}:4567/${GITLAB_REPO_PYTHON}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                  \$DOCKER_REGISTRY/\$ECR_REPO_PYTHON\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG

              # Push GITLAB_REPO_VSE
              if ! docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY --rm -t \$AWSCLI ecr create-repository --repository-name \$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX --region $WISE_AWS_ECR_REGION; then
                echo "INFO: aws-cli ecr create-repository --repository-name \$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX --region $WISE_AWS_ECR_REGION failed - assuming that it's because the repo already exists in ECR"
              fi
              docker tag ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \$DOCKER_REGISTRY/\$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
              docker push \$DOCKER_REGISTRY/\$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
              if [ -z "${env.GIT_TAG_FOR_DOCKER}" ]; then
                  docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                              \$DOCKER_REGISTRY/\$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
                  docker push \$DOCKER_REGISTRY/\$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
                  docker image rm \$DOCKER_REGISTRY/\$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX:version__${env.GIT_TAG_FOR_DOCKER}_${JENKINS_BUILD_ID}
              fi

              docker image rm \
                  ${GITLAB_HOST}:4567/${GITLAB_REPO_VSE}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                  \$DOCKER_REGISTRY/\$ECR_REPO_VSE\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
            """
        }
      }
    } // uploadECR
    stage("cleanup docker") {
      steps {
        sh """
          docker container prune -f
          docker volume prune -f
          docker image prune -f
        """
      }
    }
  } // stages
}
