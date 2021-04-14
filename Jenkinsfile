pipeline {
  agent {
    node {
      label "gpu-builder"
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
    string(name: 'WISE_AWS_ECR_ACCOUNT_ID', defaultValue: '853285614468', description: 'The AWS account ID whose ECR will be used', trim: true)
    string(name: 'WISE_AWS_ECR_REGION', defaultValue: 'us-east-1', description: 'The AWS region where the ECR is located', trim: true)
    credentials( name: 'WISE_AWS_ECR_CREDENTIALS_ID', required: true, defaultValue: "simulator--aws-credentials", description: 'The credentials to be used for accessing the ECR', credentialType: 'com.cloudbees.jenkins.plugins.awscredentials.AWSCredentialsImpl')
  }

  environment {
    PYTHONUNBUFFERED = "1"
    JENKINS_BUILD_ID = "${BUILD_ID}"
    DOCKER_TAG = "build__${JENKINS_BUILD_ID}"
    GITLAB_REPO = "hdrp/scenarios/runner/jenkins"
    ECR_REPO = "wise/testcase"
    // used to keep DOCKER_REPO_SUFFIX empty
    DEFAULT_BRANCH_NAME = "master"
  }

  stages {
    stage("Git") {
      steps {
        checkout([
          $class: "GitSCM",
          branches: [[name: "refs/heads/${BRANCH_NAME}"]],
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
          if [ "${BRANCH_NAME}" != "${DEFAULT_BRANCH_NAME}" ]; then
              DOCKER_REPO_SUFFIX="/`echo ${BRANCH_NAME} | tr / -  | tr [:upper:] [:lower:]`"
          fi

          docker build -f docker/Dockerfile \
                       --pull \
                       --no-cache \
                       --build-arg PYTHON_INSTALL_ENV='SCENARIO_RUNNER__BUILD_KIND=official' \
                       --build-arg image_git_describe="\$(git describe --always --tags)" \
                       --build-arg image_git_describe_submodules="\$(git submodule | xargs)" \
                       --build-arg image_tag=\$DOCKER_TAG \
                       --build-arg image_uuidgen=\$(uuidgen) \
                       -t ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                       .
          docker build -f docker/Dockerfile.devenv \
                       --build-arg BASE_IMAGE=${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                       -t ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX/testenv:\$DOCKER_TAG \
                       .

          docker push ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG

          if [ "${BRANCH_NAME}" = "${DEFAULT_BRANCH_NAME}" ]; then
              docker tag  ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                          ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:latest
              docker push ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:latest
          fi
        """
      }
    }

/*
    stage("test") {
      steps {
        sh """
          if [ "${BRANCH_NAME}" != "${DEFAULT_BRANCH_NAME}" ]; then
              DOCKER_REPO_SUFFIX="/`echo ${BRANCH_NAME} | tr / -  | tr [:upper:] [:lower:]`"
          fi
          docker run -t ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX/testenv:\$DOCKER_TAG pytest -s -v runner/tests
        """
      }
    }
    stage("bundle") {
      steps {
        sh """
          if [ "${BRANCH_NAME}" != "${DEFAULT_BRANCH_NAME}" ]; then
              DOCKER_REPO_SUFFIX="/`echo ${BRANCH_NAME} | tr / -  | tr [:upper:] [:lower:]`"
          fi
          ./ci/make_bundle.sh ${DOCKER_TAG} ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
          mv dist/lgsvlsimulator-scenarios-\$DOCKER_TAG .
        """
      }
    }
*/
    stage("uploadECR") {
      steps {
          sh "echo Using credentials ${WISE_AWS_ECR_CREDENTIALS_ID}"
          withCredentials([[credentialsId: "${WISE_AWS_ECR_CREDENTIALS_ID}", accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY', $class: 'AmazonWebServicesCredentialsBinding']]) {
            sh """
              if [ "${BRANCH_NAME}" != "${DEFAULT_BRANCH_NAME}" ]; then
                DOCKER_REPO_SUFFIX="/`echo ${BRANCH_NAME} | tr / -  | tr [:upper:] [:lower:]`"
              fi
              DOCKER_REGISTRY="${WISE_AWS_ECR_ACCOUNT_ID}.dkr.ecr.${WISE_AWS_ECR_REGION}.amazonaws.com"

              if ! docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -t amazon/aws-cli ecr get-login-password --region $WISE_AWS_ECR_REGION | docker login --username AWS --password-stdin \$DOCKER_REGISTRY; then
                echo "ABORT: bad AWS credentials?"
                exit 1
              fi
              if ! docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -t amazon/aws-cli ecr create-repository --repository-name \$ECR_REPO\$DOCKER_REPO_SUFFIX --region $WISE_AWS_ECR_REGION; then
                echo "INFO: aws-cli ecr create-repository --repository-name \$ECR_REPO\$DOCKER_REPO_SUFFIX --region $WISE_AWS_ECR_REGION failed - assuming that it's because the repo already exists in ECR"
              fi
              docker tag ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \$DOCKER_REGISTRY/\$ECR_REPO\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
              docker push \$DOCKER_REGISTRY/\$ECR_REPO\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG

              docker image rm \
                  ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG \
                  ${GITLAB_HOST}:4567/${GITLAB_REPO}\$DOCKER_REPO_SUFFIX/testenv:\$DOCKER_TAG \
                  \$DOCKER_REGISTRY/\$ECR_REPO\$DOCKER_REPO_SUFFIX:\$DOCKER_TAG
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
