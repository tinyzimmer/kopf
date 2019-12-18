class Kopf < Formula
  include Language::Python::Virtualenv

  desc "Kubernetes Operator Pythonic Framework (Kopf)"
  homepage "https://kopf.readthedocs.io/en/latest/"
  head "https://github.com/zalando-incubator/kopf.git"
  url "https://files.pythonhosted.org/packages/48/da/dec181a951b46777892c6bafa050d875aab3376c8b6864b2672d4131ec52/kopf-0.23.2.tar.gz"
  sha256 "e361effe9708dcda47e1a78b4f08f96991db911348cec2278c5e6bb340a33926"

  depends_on "python3"
#   depends_on "help2man" => :build  #??? TODO: https://github.com/Homebrew/homebrew-core/blob/37e7203b351fce859178ea351cb2c377a04cfbf5/Formula/fail2ban.rb
  depends_on "sphinx-doc" => :build
  # TODO: extensions are forgotten! And so, the build fails.

#   option "with-kubernetes", "Description of the option"
#   option "without-pykube-ng", "Another description"
#   if build.with? "ham"
#   end
#   if build.without? "ham"
#   end

  resource "aiohttp" do
    url "https://files.pythonhosted.org/packages/00/94/f9fa18e8d7124d7850a5715a0b9c0584f7b9375d331d35e157cee50f27cc/aiohttp-3.6.2.tar.gz"
    sha256 "259ab809ff0727d0e834ac5e8a283dc5e3e0ecc30c4d80b3cd17a4139ce1f326"
  end

  resource "aiojobs" do
    url "https://files.pythonhosted.org/packages/57/c5/9eb091930d6574002d1721dab5ca15a1bd69ed5dc8e654159d27223cdd3b/aiojobs-0.2.2.tar.gz"
    sha256 "8e4b3e3d1bdb970bdaf8f8cd5eb4e4ff3e0e01a4abd22b4f73a87002a5ae4005"
  end

  resource "async-timeout" do
    url "https://files.pythonhosted.org/packages/a1/78/aae1545aba6e87e23ecab8d212b58bb70e72164b67eb090b81bb17ad38e3/async-timeout-3.0.1.tar.gz"
    sha256 "0c3c816a028d47f659d6ff5c745cb2acf1f966da1fe5c19c77a70282b25f4c5f"
  end

  resource "attrs" do
    url "https://files.pythonhosted.org/packages/98/c3/2c227e66b5e896e15ccdae2e00bbc69aa46e9a8ce8869cc5fa96310bf612/attrs-19.3.0.tar.gz"
    sha256 "f7b7ce16570fe9965acd6d30101a28f62fb4a7f9e926b3bbc9b61f8b04247e72"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/41/bf/9d214a5af07debc6acf7f3f257265618f1db242a3f8e49a9b516f24523a6/certifi-2019.11.28.tar.gz"
    sha256 "25b64c7da4cd7479594d035c08c2d809eb4aab3a26e5a990ea98cc450c320f1f"
  end

  resource "chardet" do
    url "https://files.pythonhosted.org/packages/fc/bb/a5768c230f9ddb03acc9ef3f0d4a3cf93462473795d18e9535498c8f929d/chardet-3.0.4.tar.gz"
    sha256 "84ab92ed1c4d4f16916e05906b6b75a6c0fb5db821cc65e70cbd64a3e2a5eaae"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/f8/5c/f60e9d8a1e77005f664b76ff8aeaee5bc05d0a91798afd7f53fc998dbc47/Click-7.0.tar.gz"
    sha256 "5b94b49521f6456670fdb30cd82a4eca9412788a93fa6dd6df72c94d5a8ff2d7"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/ad/13/eb56951b6f7950cadb579ca166e448ba77f9d24efc03edd7e55fa57d04b7/idna-2.8.tar.gz"
    sha256 "c357b3f628cf53ae2c4c05627ecc484553142ca23264e593d327bcde5e9c3407"
  end

  resource "iso8601" do
    url "https://files.pythonhosted.org/packages/45/13/3db24895497345fb44c4248c08b16da34a9eb02643cea2754b21b5ed08b0/iso8601-0.1.12.tar.gz"
    sha256 "49c4b20e1f38aa5cf109ddcd39647ac419f928512c869dc01d5c7098eddede82"
  end

  resource "multidict" do
    url "https://files.pythonhosted.org/packages/34/68/38290d44ea34dae6d52719f0c94bd09951387cec75e36cdce6805b5f27e9/multidict-4.7.1.tar.gz"
    sha256 "d7b6da08538302c5245cd3103f333655ba7f274915f1f5121c4f4b5fbdb3febe"
  end

  resource "pykube-ng" do
    url "https://files.pythonhosted.org/packages/66/b9/196f989a395f6253a858bb193c7d49f1d025697eca6f5a82b326bbbc9f9f/pykube-ng-19.10.0.tar.gz"
    sha256 "440b4183719e673c11b7cd68669d3ba0b710c192834d16bd7766dfb6df9737b2"
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/8d/c9/e5be955a117a1ac548cdd31e37e8fd7b02ce987f9655f5c7563c656d5dcb/PyYAML-5.2.tar.gz"
    sha256 "c0ee8eca2c582d29c3c2ec6e2c4f703d1b7f1fb10bc72317355a746057e7346c"
  end

  resource "requests" do
    url "https://files.pythonhosted.org/packages/01/62/ddcf76d1d19885e8579acb1b1df26a852b03472c0e46d2b959a714c90608/requests-2.22.0.tar.gz"
    sha256 "11e007a8a2aa0323f5a921e9e6a2d7e4e67d9877e85773fba9ba6419025cbeb4"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/e7/dd/f1713bc6638cc3a6a23735eff6ee09393b44b96176d3296693ada272a80b/typing_extensions-3.7.4.1.tar.gz"
    sha256 "091ecc894d5e908ac75209f10d5b4f118fbdb2eb1ede6a63544054bb1edb41f2"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/ad/fc/54d62fa4fc6e675678f9519e677dfc29b8964278d75333cf142892caf015/urllib3-1.25.7.tar.gz"
    sha256 "f3c5fd51747d450d4dcf6f923c81f78f811aab8205fda64b0aba34a4e48b0745"
  end

  resource "yarl" do
    url "https://files.pythonhosted.org/packages/d6/67/6e2507586eb1cfa6d55540845b0cd05b4b77c414f6bca8b00b45483b976e/yarl-1.4.2.tar.gz"
    sha256 "58cd9c469eced558cd81aa3f484b2924e8897049e06889e8ff2510435b7ef74b"
  end

  def install
    virtualenv_create(libexec, "python3")
    virtualenv_install_with_resources

#     # TODO: sphinx-build -b man .   _build  && cp docs/_build/kopf.1 share/man/
#     # TODO: but first, install Sphinx and deps with pinned versions, tarballs, sha256.
#     cd "docs" do
# #         ENV["SPHINX"] = Formula["sphinx-doc"].opt_bin/"sphinx-build"
#         system "sphinx-build", "-b", "man", ".", "_build"
#         man1.install "_build/kopf.1"
#     end
  end

  test do
    false
  end
end
