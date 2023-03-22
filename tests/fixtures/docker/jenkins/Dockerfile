FROM jenkins/jenkins:lts-jdk11
ENV JAVA_OPTS -Djenkins.install.runSetupWizard=false
COPY security.groovy /usr/share/jenkins/ref/init.groovy.d/security.groovy
RUN jenkins-plugin-cli --plugins pipeline-model-definition
