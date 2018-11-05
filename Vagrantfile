# -*- mode: ruby -*-
# vi: set ft=ruby :

$script = <<SCRIPT
echo I am provisioning...
date > /etc/vagrant_provisioned_at
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.provision "shell", inline: $script
end

Vagrant::Config.run do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.host_name = "postgresql"

  config.vm.provision :shell, :path => "vagrant.sh"

  # PostgreSQL Server port forwarding
  config.vm.forward_port 5432, 15432
end
