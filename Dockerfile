FROM continuumio/miniconda3

# set a directory for the app
WORKDIR /usr/src/app

# Update aptitude with new repo
RUN apt-get update

# Install software 
RUN apt-get install -y git

ARG SSH_PRIVATE_KEY
ENV SSH_PRIVATE_KEY=$SSH_PRIVATE_KEY

RUN mkdir /root/.ssh/
RUN echo "${SSH_PRIVATE_KEY}" > /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa
RUN touch /root/.ssh/known_hosts
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

# copy all the files to the container
COPY . .

# Add the conda-forge channel to the list of channels
RUN conda config --add channels conda-forge

# install dependencies
RUN conda install --yes --file conda_requirements.txt

# Install pip packages
RUN pip install -r pip_requirements.txt

# Install git packages
RUN git clone git@github.com:Deltares/hydromt_fiat.git
WORKDIR /usr/src/app/hydromt_fiat
RUN pip install .

WORKDIR /usr/src/app
RUN git clone git@github.com:Deltares/fiat_toolbox.git
WORKDIR /usr/src/app/fiat_toolbox
RUN pip install .

WORKDIR /usr/src/app
RUN git clone -b storage_volume git@github.com:Deltares/hydromt_sfincs.git
WORKDIR /usr/src/app/hydromt_sfincs
RUN pip install .

WORKDIR /usr/src/app
RUN git clone git@github.com:Deltares/Delft-FIAT.git
WORKDIR /usr/src/app/Delft-FIAT
RUN pip install .

