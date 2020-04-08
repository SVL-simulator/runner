FROM python:3.6

ADD externals /app/externals
WORKDIR /apps

RUN cd /app/externals/Scenic && python setup.py install
RUN cd /app/externals/VerifAI && python setup.py install
RUN cd /app/externals/dreamview-cyber && python setup.py install
RUN cd /app/externals/PythonApi && python setup.py install

COPY docker/get_scenic_lgsvl /opt/scenic_lgsvl/
COPY scripts/scenic_lgsvl.sh /opt/scenic_lgsvl/

RUN chmod +x /opt/scenic_lgsvl/get_scenic_lgsvl && ln -s /opt/scenic_lgsvl/get_scenic_lgsvl /usr/bin
