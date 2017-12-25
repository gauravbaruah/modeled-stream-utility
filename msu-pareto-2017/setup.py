from distutils.core import setup
from Cython.Build import cythonize

setup(
        name = 'cython msu computations',
        ext_modules = cythonize(
                'cython_computations.pyx',
                language='c++')
)
