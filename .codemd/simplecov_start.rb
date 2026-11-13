require "bundler/setup"
require "simplecov"
SimpleCov.command_name "codemd"
SimpleCov.start do
  coverage_dir ".codemd-ruby-coverage"
end
