FROM python:3.9-slim

# setting up a directory inside each container to make sure the operations run
WORKDIR /application 
# this allows for COPY/RUN...and others to function

# copy has 2 parameters, from where --> to where
# we want to copy the current directory contents(files) into each of the 
# containers we make
# shortcut (.) --> the . is for the path/directory we are in
COPY . /application

# making sure the directory (the ones for each container) exist each time
# even if they exist it will still run this command
RUN mkdir -p /sync

# exposing the ports but dont really need to
# EXPOSE 5000-6000

# now to actually running the application --> run what is in the /application
# since each node is separate container, they will each run execue this 
# command (clientServer.py) on their own (independently)
CMD ["python", "clientServer.py"]
