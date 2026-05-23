from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class LogCraftPlaygroundConan(ConanFile):
    name = "logcraft_playground"
    version = "0.1.0"
    package_type = "application"
    description = "Public LogCraft playground scenarios and CLI consumer."
    settings = "os", "arch", "compiler", "build_type"

    exports_sources = (
        "CMakeLists.txt",
        "README.md",
        "scenario_reference.md",
        "cli/*",
        "cli/src/*",
        "scenario/*",
        "scenario/*/*",
        "scenario/*/*/*",
    )

    def requirements(self):
        self.requires("logcraft_core/1.3.6")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generator = "Ninja"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
