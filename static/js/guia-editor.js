/* Editor de blocos do Guia. A validação e sanitização definitivas são do servidor.
   Não há bloqueios globais de teclado, clipboard ou eventos do portal. */
(function () {
  'use strict';

  function acompanharMidia(elemento) {
    var aviso = elemento.parentElement.querySelector('.guia-midia-erro');
    if (!aviso) return;
    elemento.addEventListener('error', function () { aviso.hidden = false; });
    elemento.addEventListener(elemento.tagName === 'VIDEO' ? 'loadedmetadata' : 'load', function () { aviso.hidden = true; });
    if (elemento.tagName === 'IMG' && elemento.complete && !elemento.naturalWidth) aviso.hidden = false;
    if (elemento.tagName === 'VIDEO' && elemento.error) aviso.hidden = false;
  }
  document.querySelectorAll('[data-guia-midia]').forEach(acompanharMidia);

  var formulario = document.getElementById('guiaEditor');
  if (!formulario) return;
  var lista = document.getElementById('guiaEditorBlocos');
  var serializado = document.getElementById('guiaBlocosJson');
  var inicial = document.getElementById('guiaBlocosIniciais');
  var avisoErro = document.getElementById('guiaEditorErro');
  var avisoStatus = document.getElementById('guiaEditorStatus');
  var desfazer = document.getElementById('guiaDesfazerRemocao');
  var salvar = document.getElementById('guiaSalvar');
  var videoDisponivel = formulario.dataset.videoDisponivel === 'true';
  var contador = 0;
  var removidos = [];
  var urlsLocais = new Set();
  var MAX_BLOCOS = 80;
  var MAX_MIDIAS = 12;
  var MIB = 1024 * 1024;

  function elemento(tag, classe, texto) {
    var no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto !== undefined) no.textContent = texto;
    return no;
  }
  function erro(mensagem) {
    avisoErro.textContent = mensagem || '';
    avisoErro.hidden = !mensagem;
  }
  function anunciar(mensagem) { avisoStatus.textContent = mensagem; }
  function botao(texto, atributo, valor) {
    var no = elemento('button', 'btn-ghost btn-sm-x', texto);
    no.type = 'button';
    if (atributo) no.setAttribute(atributo, valor === undefined ? '' : valor);
    return no;
  }
  function linkSeguro(valor) {
    var texto = String(valor || '').trim();
    if (!texto || texto.length > 2048 || texto.indexOf('\\') !== -1 || /[\u0000-\u0020\u007f]/.test(texto)) return null;
    if (texto.charAt(0) === '#' || (texto.charAt(0) === '/' && texto.charAt(1) !== '/')) return texto;
    try {
      var url = new URL(texto);
      if (['http:', 'https:'].indexOf(url.protocol) !== -1 && url.hostname && !url.username && !url.password) return texto;
      return url.protocol === 'mailto:' && url.pathname.indexOf('@') !== -1 && !url.host ? texto : null;
    } catch (_) { return null; }
  }
  function urlMidiaSegura(valor) {
    try {
      var url = new URL(String(valor || ''), window.location.origin);
      return valor && url.origin === window.location.origin && ['http:', 'https:'].indexOf(url.protocol) !== -1 ? url.href : '';
    } catch (_) { return ''; }
  }
  function htmlSeguro(html) {
    /* template é inerte: elementos não são inseridos na página antes da limpeza.
       A mesma limpeza protege o rerender de um formulário rejeitado pelo servidor. */
    var modelo = document.createElement('template');
    modelo.innerHTML = String(html || '');
    var permitidos = ['P', 'H2', 'H3', 'STRONG', 'EM', 'UL', 'OL', 'LI', 'A', 'BR', 'BLOCKQUOTE'];
    function limpar(raiz) {
      Array.from(raiz.childNodes).forEach(function (no) {
        if (no.nodeType === Node.COMMENT_NODE) { no.remove(); return; }
        if (no.nodeType !== Node.ELEMENT_NODE) return;
        if (['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'EMBED', 'SVG', 'MATH', 'TEMPLATE'].indexOf(no.tagName) !== -1) { no.remove(); return; }
        limpar(no);
        var nome = {DIV: 'P', B: 'STRONG', I: 'EM'}[no.tagName] || no.tagName;
        if (permitidos.indexOf(nome) === -1) { no.replaceWith.apply(no, Array.from(no.childNodes)); return; }
        var href = no.tagName === 'A' ? linkSeguro(no.getAttribute('href')) : null;
        var limpo = document.createElement(nome.toLowerCase());
        while (no.firstChild) limpo.appendChild(no.firstChild);
        if (href) {
          limpo.setAttribute('href', href);
          if (/^https?:/i.test(href)) { limpo.setAttribute('target', '_blank'); limpo.setAttribute('rel', 'noopener noreferrer'); }
        }
        no.replaceWith(limpo);
      });
    }
    limpar(modelo.content);
    return modelo.innerHTML;
  }
  function atualizar() {
    var blocos = [];
    var linhas = Array.from(lista.children);
    linhas.forEach(function (linha, indice) {
      var tipo = linha.dataset.guiaTipo;
      var titulo = linha.querySelector('[data-guia-bloco-titulo]');
      titulo.textContent = 'Bloco ' + (indice + 1) + ' — ' + (tipo === 'texto' ? 'Texto' : tipo === 'video' ? 'Vídeo' : 'Imagem');
      linha.querySelector('[data-guia-mover="acima"]').disabled = indice === 0;
      linha.querySelector('[data-guia-mover="abaixo"]').disabled = indice === linhas.length - 1;
      if (tipo === 'texto') {
        blocos.push({tipo: 'texto', html: htmlSeguro(linha.querySelector('[contenteditable]').innerHTML)});
      } else {
        var identificador = linha.dataset.guiaId;
        blocos.push({tipo: 'midia', id: /^\d+$/.test(identificador) ? Number(identificador) : identificador, tipo_midia: tipo,
          legenda: linha.querySelector('[data-guia-legenda]').value, alt: linha.querySelector('[data-guia-alt]').value});
      }
    });
    serializado.value = JSON.stringify(blocos);
    document.getElementById('guiaEditorVazio').hidden = linhas.length > 0;
    desfazer.disabled = !removidos.length;
  }
  function restaurarSelecao(editor, estado) {
    editor.focus();
    var selecao = window.getSelection();
    selecao.removeAllRanges();
    try {
      if (!estado.faixa || !editor.contains(estado.faixa.commonAncestorContainer)) throw new Error('sem seleção');
      selecao.addRange(estado.faixa);
    } catch (_) {
      var faixa = document.createRange(); faixa.selectNodeContents(editor); faixa.collapse(false); selecao.addRange(faixa);
    }
  }
  function prepararTexto(linha, bloco, chave) {
    var toolbar = elemento('div', 'guia-editor-toolbar');
    toolbar.setAttribute('role', 'group'); toolbar.setAttribute('aria-label', 'Formatar texto do bloco');
    var estilo = elemento('select', 'form-select');
    estilo.setAttribute('data-guia-estilo', ''); estilo.setAttribute('aria-label', 'Estilo de texto');
    [['p', 'Parágrafo'], ['h2', 'Título'], ['h3', 'Subtítulo']].forEach(function (opcao) { var item = elemento('option', '', opcao[1]); item.value = opcao[0]; estilo.appendChild(item); });
    toolbar.appendChild(estilo);
    var editor = elemento('div', 'guia-editor-campo');
    editor.id = 'guiaTexto' + chave; editor.contentEditable = 'true'; editor.setAttribute('role', 'textbox');
    editor.setAttribute('aria-multiline', 'true'); editor.setAttribute('aria-label', 'Texto do tutorial');
    editor.setAttribute('aria-describedby', 'guiaConteudoAjuda');
    editor.innerHTML = htmlSeguro(bloco.html || '<p><br></p>');
    var estado = {faixa: null};
    function guardar() {
      var selecao = window.getSelection();
      if (selecao.rangeCount && editor.contains(selecao.anchorNode) && editor.contains(selecao.focusNode)) estado.faixa = selecao.getRangeAt(0).cloneRange();
    }
    ['keyup', 'mouseup', 'touchend', 'input', 'focusout'].forEach(function (nome) { editor.addEventListener(nome, guardar); });
    estilo.addEventListener('mousedown', guardar);
    estilo.addEventListener('change', function () { restaurarSelecao(editor, estado); document.execCommand('formatBlock', false, estilo.value); guardar(); atualizar(); });
    [['bold', 'Negrito'], ['italic', 'Itálico'], ['insertOrderedList', 'Lista numerada'], ['insertUnorderedList', 'Lista com marcadores'], ['createLink', 'Adicionar link'], ['unlink', 'Remover link']].forEach(function (comando) {
      var controle = botao(comando[1], 'data-guia-comando', comando[0]);
      controle.addEventListener('mousedown', function (evento) { guardar(); evento.preventDefault(); });
      controle.addEventListener('click', function () {
        guardar();
        var valor = null;
        if (comando[0] === 'createLink') {
          valor = window.prompt('Endereço do link (https://..., /caminho do portal ou #seção):');
          if (valor === null) return;
          valor = linkSeguro(valor);
          if (!valor) { erro('Informe um link HTTP, HTTPS, de e-mail ou um caminho interno válido.'); return; }
        }
        restaurarSelecao(editor, estado); document.execCommand(comando[0], false, valor); guardar(); erro(''); atualizar();
      });
      toolbar.appendChild(controle);
    });
    /* Cola e arrasto locais inserem texto simples. Atalhos nativos de cópia,
       recorte, seleção, desfazer e refazer continuam a cargo do navegador. */
    editor.addEventListener('paste', function (evento) { evento.preventDefault(); document.execCommand('insertText', false, evento.clipboardData.getData('text/plain')); });
    editor.addEventListener('drop', function (evento) { evento.preventDefault(); restaurarSelecao(editor, estado); document.execCommand('insertText', false, evento.dataTransfer ? evento.dataTransfer.getData('text/plain') : ''); });
    editor.addEventListener('input', atualizar);
    linha.appendChild(toolbar); linha.appendChild(editor);
  }
  function campoTexto(rotulo, atributo, valor, chave, maximo) {
    var grupo = elemento('div'); var label = elemento('label', 'nexo-label', rotulo); var campo = elemento('input', 'form-control');
    campo.type = 'text'; campo.id = atributo + chave; campo.setAttribute(atributo, ''); campo.value = valor || ''; campo.maxLength = maximo;
    label.htmlFor = campo.id; grupo.appendChild(label); grupo.appendChild(campo); campo.addEventListener('input', atualizar); return grupo;
  }
  function prepararMidia(linha, bloco, chave) {
    var tipo = linha.dataset.guiaTipo;
    var identificador = bloco.id === undefined ? 'nova_' + chave : String(bloco.id);
    linha.dataset.guiaId = identificador;
    var controle = elemento('input', 'form-control'); controle.type = 'file'; controle.name = 'midia_' + identificador;
    controle.id = 'guiaArquivo' + chave; controle.setAttribute('data-guia-file', ''); controle.accept = tipo === 'video' ? '.mp4,video/mp4' : '.png,.jpg,.jpeg,.webp,.gif';
    if (tipo === 'video' && !videoDisponivel) controle.disabled = true;
    var label = elemento('label', 'nexo-label', bloco.url ? 'Substituir ' + (tipo === 'video' ? 'vídeo' : 'imagem') : 'Selecionar ' + (tipo === 'video' ? 'vídeo' : 'imagem'));
    label.htmlFor = controle.id; linha.appendChild(label); linha.appendChild(controle);
    var previa = elemento('div', 'guia-editor-midia-preview');
    var status = elemento('p', 'field-hint'); status.setAttribute('role', 'status');
    var url = urlMidiaSegura(bloco.url);
    if (url) {
      var midia = elemento(tipo === 'video' ? 'video' : 'img'); midia.src = url;
      if (tipo === 'video') { midia.controls = true; midia.preload = 'metadata'; midia.setAttribute('playsinline', ''); midia.setAttribute('aria-label', bloco.alt || 'Vídeo atual'); }
      else midia.alt = bloco.alt || 'Imagem atual do tutorial';
      midia.addEventListener('error', function () { status.textContent = 'A mídia atual está indisponível. Você pode substituí-la ou tentar novamente mais tarde.'; });
      previa.appendChild(midia);
    }
    linha.appendChild(previa); linha.appendChild(status);
    controle.addEventListener('change', function () {
      var arquivo = controle.files[0]; controle.setCustomValidity(''); status.textContent = '';
      if (controle.dataset.urlLocal) { URL.revokeObjectURL(controle.dataset.urlLocal); urlsLocais.delete(controle.dataset.urlLocal); delete controle.dataset.urlLocal; }
      if (!arquivo) { atualizar(); return; }
      var extensao = arquivo.name.split('.').pop().toLowerCase();
      var valido = tipo === 'video' ? extensao === 'mp4' : ['png', 'jpg', 'jpeg', 'webp', 'gif'].indexOf(extensao) !== -1;
      var maximo = (tipo === 'video' ? 8 : 3) * MIB;
      if (!valido || arquivo.size > maximo || !arquivo.size) {
        var mensagem = !valido ? 'Formato não suportado para este bloco.' : 'O arquivo está vazio ou ultrapassa o limite de ' + (tipo === 'video' ? '8' : '3') + ' MiB.';
        controle.setCustomValidity(mensagem); status.textContent = mensagem; atualizar(); return;
      }
      previa.replaceChildren();
      if (tipo === 'imagem') {
        var local = URL.createObjectURL(arquivo); urlsLocais.add(local); controle.dataset.urlLocal = local;
        var imagem = elemento('img'); imagem.src = local; imagem.alt = 'Prévia da imagem selecionada'; previa.appendChild(imagem);
        imagem.addEventListener('error', function () { status.textContent = 'Não foi possível abrir a prévia desta imagem. Verifique o arquivo antes de salvar.'; });
        status.textContent = 'Imagem selecionada. O conteúdo será validado ao salvar.';
      } else status.textContent = arquivo.name + ' selecionado. Salve como rascunho para conferir o vídeo na prévia.';
      atualizar();
    });
    var legendas = elemento('div', 'guia-editor-legenda');
    legendas.appendChild(campoTexto('Legenda', 'data-guia-legenda', bloco.legenda, chave, 500));
    legendas.appendChild(campoTexto(tipo === 'video' ? 'Descrição do vídeo' : 'Texto alternativo da imagem', 'data-guia-alt', bloco.alt, chave, 240));
    linha.appendChild(legendas);
  }
  function adicionar(bloco, focalizar) {
    if (lista.children.length >= MAX_BLOCOS) { erro('Use até ' + MAX_BLOCOS + ' blocos por tutorial.'); return; }
    var tipo = bloco.tipo === 'texto' ? 'texto' : bloco.tipo_midia === 'video' ? 'video' : 'imagem';
    if (tipo !== 'texto' && lista.querySelectorAll('[data-guia-id]').length >= MAX_MIDIAS) { erro('Use até ' + MAX_MIDIAS + ' mídias por tutorial.'); return; }
    var chave = 'b' + (++contador);
    var linha = elemento('section', 'guia-editor-bloco'); linha.dataset.guiaTipo = tipo;
    var cabecalho = elemento('div', 'guia-editor-bloco-cabecalho');
    var titulo = elemento('h3'); titulo.id = 'guiaBlocoTitulo' + chave; titulo.setAttribute('data-guia-bloco-titulo', ''); linha.setAttribute('aria-labelledby', titulo.id);
    var acoes = elemento('div', 'guia-editor-bloco-acoes');
    [['acima', 'Mover para cima'], ['abaixo', 'Mover para baixo']].forEach(function (acao) {
      var mover = botao(acao[1], 'data-guia-mover', acao[0]);
      mover.addEventListener('click', function () {
        var vizinho = acao[0] === 'acima' ? linha.previousElementSibling : linha.nextElementSibling;
        if (!vizinho) return;
        if (acao[0] === 'acima') lista.insertBefore(linha, vizinho); else lista.insertBefore(vizinho, linha);
        atualizar(); anunciar('Ordem do bloco atualizada.');
        var controle = linha.querySelector('[data-guia-mover="' + acao[0] + '"]');
        if (!controle.disabled) controle.focus(); else { titulo.setAttribute('tabindex', '-1'); titulo.focus(); }
      });
      acoes.appendChild(mover);
    });
    var remover = botao('Remover bloco', 'data-guia-remover'); remover.classList.add('is-danger');
    remover.addEventListener('click', function () { removidos.push({linha: linha, proximo: linha.nextElementSibling}); linha.remove(); atualizar(); anunciar('Bloco removido desta edição. Use “Desfazer remoção” para recuperá-lo antes de salvar.'); desfazer.focus(); });
    acoes.appendChild(remover); cabecalho.appendChild(titulo); cabecalho.appendChild(acoes); linha.appendChild(cabecalho);
    if (tipo === 'texto') prepararTexto(linha, bloco, chave); else prepararMidia(linha, bloco, chave);
    lista.appendChild(linha); atualizar(); erro('');
    if (focalizar) linha.querySelector('[contenteditable], input[type="file"]').focus();
  }
  desfazer.addEventListener('click', function () {
    var ultimo = removidos.pop(); if (!ultimo) return;
    if (lista.children.length >= MAX_BLOCOS) { removidos.push(ultimo); erro('Remova outro bloco antes de restaurar este.'); return; }
    lista.insertBefore(ultimo.linha, ultimo.proximo && ultimo.proximo.parentElement === lista ? ultimo.proximo : null);
    atualizar(); anunciar('Remoção desfeita.'); ultimo.linha.querySelector('[contenteditable], input[type="file"]').focus();
  });
  formulario.querySelectorAll('[data-guia-adicionar]').forEach(function (controle) {
    controle.addEventListener('click', function () { adicionar(controle.dataset.guiaAdicionar === 'texto' ? {tipo: 'texto', html: ''} : {tipo: 'midia', tipo_midia: controle.dataset.guiaAdicionar}, true); });
  });
  formulario.addEventListener('submit', function (evento) {
    atualizar(); erro('');
    var textos = Array.from(lista.querySelectorAll('[contenteditable]'));
    if (!textos.some(function (texto) { return texto.textContent.trim(); }) && !lista.querySelector('[data-guia-id]')) { evento.preventDefault(); erro('Escreva o conteúdo ou adicione uma mídia ao tutorial.'); if (textos[0]) textos[0].focus(); return; }
    var arquivos = Array.from(lista.querySelectorAll('[data-guia-file]'));
    var total = arquivos.reduce(function (soma, campo) { return soma + (campo.files[0] ? campo.files[0].size : 0); }, 0);
    var novoVazio = arquivos.find(function (campo) { return campo.name.indexOf('midia_nova_') === 0 && !campo.files.length; });
    if (novoVazio) { evento.preventDefault(); erro('Selecione um arquivo para cada nova mídia ou remova o bloco vazio.'); novoVazio.focus(); return; }
    if (total > 19 * MIB) { evento.preventDefault(); erro('Envie até 19 MiB de arquivos por vez para reservar espaço ao texto e ao formulário. Salve e adicione as demais mídias em outra edição.'); }
  });
  window.addEventListener('pagehide', function () { urlsLocais.forEach(function (url) { URL.revokeObjectURL(url); }); urlsLocais.clear(); });
  try {
    var blocos = JSON.parse(inicial.textContent);
    if (!Array.isArray(blocos)) throw new Error('conteúdo inválido');
    blocos.forEach(function (bloco) { adicionar(bloco, false); });
    if (!lista.children.length) adicionar({tipo: 'texto', html: ''}, false);
    document.getElementById('guiaEditorCarregando').hidden = true;
    salvar.disabled = false; atualizar();
  } catch (_) { erro('Não foi possível carregar o editor. Recarregue a página antes de salvar.'); }
}());
