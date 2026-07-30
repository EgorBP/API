import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckSquare,
  Database,
  ImageOff,
  KeyRound,
  Library,
  LogOut,
  Moon,
  Plus,
  Search,
  Sun,
  Trash2,
  Upload,
  User,
  X,
  Check,
} from 'lucide-react';
import { api, getStoredTokens, setStoredTokens } from './api/client.js';
import { DEV_MODE, TELEGRAM_BOT_USERNAME, resolveMediaUrl } from './config.js';
import { useAsyncAction } from './hooks/useAsyncAction.js';
import { useTokens } from './hooks/useTokens.js';
import { uniqueTags } from './utils/tags.js';

const defaultSearch = {
  sorting: 'desc',
  tags: '',
};

const defaultLibrary = {
  tags: '',
};

const PAGE_SIZE = 24;

const ACCENT_THEMES = [
  { id: 'mono', label: 'Monochrome' },
  { id: 'teal', label: 'Teal' },
  { id: 'orange', label: 'Orange' },
  { id: 'blue', label: 'Blue' },
  { id: 'pink', label: 'Pink' },
];

function toQuery(form) {
  return {
    sorting: form.sorting,
    tags: uniqueTags(form.tags),
    limit: PAGE_SIZE,
  };
}

function UserProfileMenu({ profile, onLogout, devMode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [nameMode, setNameMode] = useState(() => localStorage.getItem('profile_display_mode') || 'username');
  const [devIdMode, setDevIdMode] = useState(() => localStorage.getItem('profile_dev_id_mode') || 'id');
  const containerRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('profile_display_mode', nameMode);
  }, [nameMode]);

  useEffect(() => {
    localStorage.setItem('profile_dev_id_mode', devIdMode);
  }, [devIdMode]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const avatar = profile?.photo_url || profile?.avatar || profile?.photoUrl;
  const username = profile?.username ? `@${profile.username}` : 'Юзернейм';
  const firstName = profile?.first_name || profile?.username || 'Имя';
  const userId = profile?.id !== undefined ? `ID: ${profile.id}` : 'ID: --';
  const tgId = profile?.telegram_id || profile?.tg_id ? `TG ID: ${profile.telegram_id || profile.tg_id}` : userId;

  let displayText = '';
  if (devMode) {
    displayText = devIdMode === 'id' ? userId : tgId;
  } else {
    displayText = nameMode === 'username' ? username : firstName;
  }

  function toggleDisplayMode() {
    if (devMode) {
      setDevIdMode((prev) => (prev === 'id' ? 'tg_id' : 'id'));
    } else {
      setNameMode((prev) => (prev === 'username' ? 'name' : 'username'));
    }
  }

  let switchButtonText = '';
  if (devMode) {
    switchButtonText = devIdMode === 'id' ? 'Сменить на Telegram ID' : 'Сменить на User ID';
  } else {
    switchButtonText = nameMode === 'username' ? 'Сменить на имя' : 'Сменить на юзернейм';
  }

  return (
    <div className="userProfileMenuContainer" ref={containerRef}>
      <button
        type="button"
        className="userProfileButton"
        onClick={() => setIsOpen((prev) => !prev)}
        title="Профиль пользователя"
      >
        {avatar ? (
          <img src={avatar} alt="Аватар" className="userAvatarImg" />
        ) : (
          <div className="userAvatarFallback">
            <User size={18} />
          </div>
        )}
        <span className="userProfileText">{displayText}</span>
      </button>

      {isOpen && (
        <div className="userProfileDropdown">
          <button
            type="button"
            className="dropdownMenuItem"
            onClick={toggleDisplayMode}
          >
            <User size={16} />
            <span>{switchButtonText}</span>
          </button>
          <div className="dropdownDivider" />
          <button
            type="button"
            className="dropdownMenuItem danger"
            onClick={() => {
              setIsOpen(false);
              onLogout();
            }}
          >
            <LogOut size={16} />
            <span>Выйти</span>
          </button>
        </div>
      )}
    </div>
  );
}

function TagInput({ tags = '', onChange, placeholder = 'Введите теги через запятую...' }) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef(null);

  const parsedTags = useMemo(() => {
    if (Array.isArray(tags)) return tags;
    if (typeof tags === 'string') {
      return tags.split(',').map((t) => t.trim()).filter(Boolean);
    }
    return [];
  }, [tags]);

  function commitTags(tagsList) {
    onChange(tagsList.join(', '));
  }

  function addTag(rawText) {
    const parts = rawText.split(',').map((t) => t.trim()).filter(Boolean);
    if (parts.length === 0) return;
    const nextTags = Array.from(new Set([...parsedTags, ...parts]));
    commitTags(nextTags);
    setInputValue('');
  }

  function handleInputChange(e) {
    const val = e.target.value;
    if (val.includes(',')) {
      addTag(val);
    } else {
      setInputValue(val);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (inputValue.trim()) {
        addTag(inputValue);
      }
    } else if (e.key === 'Backspace' && !inputValue && parsedTags.length > 0) {
      const nextTags = parsedTags.slice(0, -1);
      commitTags(nextTags);
    }
  }

  function removeTag(indexToRemove) {
    const nextTags = parsedTags.filter((_, idx) => idx !== indexToRemove);
    commitTags(nextTags);
  }

  function clearAll() {
    commitTags([]);
    setInputValue('');
  }

  const hasContent = parsedTags.length > 0 || inputValue.length > 0;

  return (
    <div className="tagInputContainer" onClick={() => inputRef.current?.focus()}>
      {parsedTags.map((tag, idx) => (
        <span key={`${tag}-${idx}`} className="tagInputBadge">
          #{tag}
          <button
            type="button"
            className="tagInputRemove"
            onClick={(e) => {
              e.stopPropagation();
              removeTag(idx);
            }}
          >
            <X size={14} />
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        type="text"
        className="tagInputNative"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (inputValue.trim()) addTag(inputValue);
        }}
        placeholder={parsedTags.length === 0 ? placeholder : ''}
      />
      {hasContent && (
        <button
          type="button"
          className="tagInputClearAll"
          onClick={(e) => {
            e.stopPropagation();
            clearAll();
          }}
          title="Очистить все теги"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}

function Status({ action }) {
  if (action.error) {
    return <p className="status error">{action.error}</p>;
  }

  if (action.message) {
    return <p className="status success">{action.message}</p>;
  }

  return null;
}

function SubmitButton({ loading, icon: Icon, children, danger = false, disabled = false }) {
  return (
    <button className={danger ? 'button danger' : 'button'} type="submit" disabled={loading || disabled}>
      <Icon size={17} />
      {loading ? 'Выполняю...' : children}
    </button>
  );
}

function GifImage({ gif }) {
  const [sourceIndex, setSourceIndex] = useState(0);
  const src = resolveMediaUrl(gif.file_path);
  const hasExtension = /\.[a-z0-9]+($|\?)/i.test(src);
  const sourceCandidates = hasExtension ? [src] : [`${src}.gif`, `${src}.mp4`, src];
  const currentSrc = sourceCandidates[sourceIndex];
  const isVideo = /\.mp4($|\?)/i.test(currentSrc) || (!hasExtension && sourceIndex === 1);

  useEffect(() => {
    setSourceIndex(0);
  }, [src]);

  function tryNextSource() {
    setSourceIndex((current) => current + 1);
  }

  if (!currentSrc || sourceIndex >= sourceCandidates.length) {
    return (
      <div className="mediaFallback">
        <ImageOff size={30} />
        <span>Файл не загрузился</span>
      </div>
    );
  }

  if (isVideo) {
    return (
      <video
        src={currentSrc}
        aria-label={`GIF ${gif.id}`}
        autoPlay
        loop
        muted
        playsInline
        preload="metadata"
        onError={tryNextSource}
      />
    );
  }

  return <img src={currentSrc} alt={`GIF ${gif.id}`} loading="lazy" onError={tryNextSource} />;
}

function GifGrid({ gifs, onGifClick, selectionMode = false, selectedIds = [], onToggleSelect }) {
  if (!gifs?.length) {
    return <div className="empty">Нет GIF для отображения.</div>;
  }

  const selectedSet = new Set(selectedIds);

  return (
    <div className="gifGrid">
      {gifs.map((gif) => {
        const isSelected = selectedSet.has(gif.id);
        return (
          <article className={`gifCard ${isSelected ? 'selected' : ''}`} key={gif.id}>
            <button
              className="gifCardButton"
              type="button"
              onClick={() => {
                if (selectionMode) {
                  onToggleSelect?.(gif.id);
                } else {
                  onGifClick?.(gif);
                }
              }}
            >
              {selectionMode && (
                <div
                  className="selectionCheckbox"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleSelect?.(gif.id);
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {}}
                  />
                </div>
              )}
              <div className="mediaFrame">
                <GifImage gif={gif} />
              </div>
            </button>
          </article>
        );
      })}
    </div>
  );
}

function GifModal({
  gif,
  tags,
  tagsEmptyHint,
  loading,
  onClose,
  editable = false,
  onSaveTags,
  onDelete,
  onTagClick,
  onAddToLibrary,
  isAdded = false,
}) {
  const [tagsInput, setTagsInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [localError, setLocalError] = useState('');
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (gif) {
      setTagsInput((tags || []).join(', '));
      setLocalError('');
      setSaving(false);
      setDeleting(false);
      setAdding(false);
    }
  }, [gif, tags]);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!gif) {
    return null;
  }

  async function handleSave() {
    const nextTags = uniqueTags(tagsInput);
    if (nextTags.length === 0) {
      setLocalError('Добавьте хотя бы один тег.');
      return;
    }

    setSaving(true);
    setLocalError('');
    try {
      await onSaveTags(gif.id, nextTags);
      onClose();
    } catch (err) {
      setLocalError(err.message || 'Не получилось сохранить теги.');
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm('Удалить эту гифку из вашей библиотеки?')) {
      return;
    }

    setDeleting(true);
    setLocalError('');
    try {
      await onDelete(gif.id);
      onClose();
    } catch (err) {
      setLocalError(err.message || 'Не получилось удалить гифку.');
      setDeleting(false);
    }
  }

  async function handleAdd() {
    if (!gif || !onAddToLibrary) return;
    setAdding(true);
    setLocalError('');
    try {
      await onAddToLibrary(gif.id, tags || []);
    } catch (err) {
      setLocalError(err.message || 'Не удалось добавить гифку.');
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="modalOverlay" onClick={onClose}>
      <div className="modalContent" onClick={(event) => event.stopPropagation()}>
        <div className="modalMedia">
          <GifImage gif={gif} />

          {onAddToLibrary && (
            <button
              type="button"
              className={`modalAdd ${isAdded ? 'success' : ''}`}
              onClick={handleAdd}
              disabled={isAdded || adding || loading}
            >
              {isAdded ? <Check size={18} /> : <Plus size={18} />}
            </button>
          )}
        </div>

        <div className="modalTags">
          {editable ? (
            <div className="modalEdit">
              <label>
                Теги
                <TagInput tags={tagsInput} onChange={setTagsInput} placeholder="смешное, коты" />
              </label>
              {localError && <p className="status error">{localError}</p>}
              <div className="buttonRow">
                <button className="button" type="button" onClick={handleSave} disabled={saving}>
                  {saving ? 'Сохраняю...' : 'Сохранить теги'}
                </button>
                <button className="dangerGhost" type="button" onClick={handleDelete} disabled={deleting}>
                  {deleting ? 'Удалить из библиотеки' : 'Удалить из библиотеки'}
                </button>
              </div>
            </div>
          ) : (
            <>
              {loading && <p className="muted">Загружаю теги...</p>}
              {!loading && tags?.length > 0 && (
                <div className="chips noPad">
                  {tags.map((tag) =>
                    onTagClick ? (
                      <button key={tag} type="button" className="chip chipButton" onClick={() => onTagClick(tag)}>
                        #{tag}
                      </button>
                    ) : (
                      <span className="chip" key={tag}>
                        #{tag}
                      </span>
                    ),
                  )}
                </div>
              )}
              {!loading && (!tags || tags.length === 0) && (
                <p className="cardHint">{tagsEmptyHint || 'Тегов пока нет.'}</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function UploadModal({ isOpen, onClose, onUpload }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [tagsInput, setTagsInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      setFile(null);
      setPreviewUrl(null);
      setTagsInput('');
      setError('');
      setLoading(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  function handleFileSelect(event) {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
      setError('');
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) {
      setError('Выберите файл.');
      return;
    }
    const tags = uniqueTags(tagsInput);
    if (tags.length === 0) {
      setError('Укажите хотя бы один тег.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await onUpload(file, tags);
      onClose();
    } catch (err) {
      setError(err.message || 'Не удалось загрузить гифку.');
    } finally {
      setLoading(false);
    }
  }

  const isVideo = file?.type?.includes('mp4') || file?.name?.endsWith('.mp4');

  return (
    <div className="modalOverlay" onClick={onClose}>
      <div className="modalContent uploadModalContent" onClick={(event) => event.stopPropagation()}>
        <button className="modalClose" type="button" onClick={onClose} aria-label="Закрыть">
          <X size={18} />
        </button>
        <h3>Добавить GIF в библиотеку</h3>

        <form onSubmit={handleSubmit} className="uploadForm">
          <input
            type="file"
            ref={fileInputRef}
            accept="image/gif,video/mp4"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />

          <div className="filePickerArea">
            {previewUrl ? (
              <div className="uploadPreviewFrame">
                {isVideo ? (
                  <video src={previewUrl} autoPlay loop muted playsInline />
                ) : (
                  <img src={previewUrl} alt="Превью" />
                )}
                <button
                  type="button"
                  className="secondaryButton changeFileBtn"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Выбрать другой файл
                </button>
              </div>
            ) : (
              <button
                type="button"
                className="fileSelectButton"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={28} />
                <span>Нажмите, чтобы выбрать GIF или MP4</span>
              </button>
            )}
          </div>

          <label>
            Теги
            <TagInput tags={tagsInput} onChange={setTagsInput} placeholder="коты, мем, реакция" />
          </label>

          {error && <p className="status error">{error}</p>}

          <SubmitButton loading={loading} icon={Upload} disabled={!file || !tagsInput}>
            Загрузить
          </SubmitButton>
        </form>
      </div>
    </div>
  );
}

function TelegramLoginWidget({ onLogin }) {
  useEffect(() => {
    if (!TELEGRAM_BOT_USERNAME) return;

    window.onTelegramAuth = onLogin;

    const container = document.getElementById('tg-login-modal-container');
    if (container) {
      container.innerHTML = '';
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://telegram.org/js/telegram-widget.js?22';
      script.setAttribute('data-telegram-login', TELEGRAM_BOT_USERNAME);
      script.setAttribute('data-size', 'large');
      script.setAttribute('data-userpic', 'true');
      script.setAttribute('data-onauth', 'onTelegramAuth(user)');
      script.setAttribute('data-request-access', 'write');
      container.appendChild(script);
    }

    return () => {
      delete window.onTelegramAuth;
    };
  }, [onLogin]);

  if (!TELEGRAM_BOT_USERNAME) {
    return <span className="muted" style={{ fontSize: '13px' }}>Задайте VITE_TELEGRAM_BOT_USERNAME в .env</span>;
  }

  return (
    <div className="telegramModalWrapper">
      <div id="tg-login-modal-container" />
    </div>
  );
}

function AuthModal({ isOpen, onClose, setTokens, refreshProfile, onSuccess, onTelegramLogin, onExtraSave }) {
  const [devTgId, setDevTgId] = useState('12345678');
  const action = useAsyncAction();

  if (!isOpen) return null;

  async function submitDevLogin(event) {
    event.preventDefault();
    const extra = {
      photo_url: null,
      username: `dev_${devTgId}`,
      first_name: `Dev User ${devTgId}`,
      id: devTgId,
      telegram_id: devTgId,
    };
    if (onExtraSave) onExtraSave(extra);

    const nextTokens = await action.run(
      () => api.auth.devLogin(devTgId)
    );
    setStoredTokens(nextTokens);
    if (setTokens) setTokens(nextTokens);
    await refreshProfile(nextTokens.access_token, extra);
    if (onSuccess) onSuccess();
  }

  return (
    <div className="modalOverlay" onClick={onClose}>
      <div className="modalContent authModalContent" onClick={(event) => event.stopPropagation()}>
        <button className="modalClose" type="button" onClick={onClose} aria-label="Закрыть">
          <X size={18} />
        </button>
        <div className="authPanel">
          <div className="authHeader">
            <h3>Вход в аккаунт</h3>
            <p className="muted">
              Авторизуйтесь, чтобы управлять своей личной библиотекой гифок.
            </p>
          </div>

          {DEV_MODE ? (
            <form className="inlineForm" onSubmit={submitDevLogin}>
              <label>
                Telegram ID (Dev Mode)
                <input
                  inputMode="numeric"
                  value={devTgId}
                  onChange={(event) => setDevTgId(event.target.value)}
                  placeholder="12345678"
                />
              </label>
              <SubmitButton loading={action.loading} icon={KeyRound}>Войти</SubmitButton>
            </form>
          ) : (
            <TelegramLoginWidget onLogin={onTelegramLogin} />
          )}

          <Status action={action} />
        </div>
      </div>
    </div>
  );
}

function PopularPage({ tokens, onOpenAuthModal }) {
  const [search, setSearch] = useState(defaultSearch);
  const [results, setResults] = useState(null);
  const [popularGifs, setPopularGifs] = useState(null);
  const [popularTags, setPopularTags] = useState(null);
  const [modalGif, setModalGif] = useState(null);
  const [modalTags, setModalTags] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [addedGifIds, setAddedGifIds] = useState(new Set());
  const action = useAsyncAction();

  async function submitSearch(event) {
    event?.preventDefault();
    const payload = await action.run(() => api.public.searchGifs(toQuery(search)));
    setResults(payload);
  }

  async function loadMoreResults() {
    if (!results?.pagination?.has_next) {
      return;
    }

    const payload = await action.run(() =>
      api.public.searchGifs({ ...toQuery(search), cursor: results.pagination.next_cursor }),
    );
    setResults((current) => ({
      data: [...(current?.data || []), ...payload.data],
      pagination: payload.pagination,
    }));
  }

  async function loadPopular() {
    const [gifs, tags] = await action.run(() =>
      Promise.all([api.public.popularGifs(), api.public.popularTags()]),
    );
    setPopularGifs(gifs);
    setPopularTags(tags);
    setResults(null);
  }

  async function runTagSearch(tag) {
    const nextSearch = { ...search, tags: tag };
    setSearch(nextSearch);
    const payload = await action.run(() => api.public.searchGifs(toQuery(nextSearch)));
    setResults(payload);
  }

  useEffect(() => {
    loadPopular();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openGifModal(gif) {
    setModalGif(gif);
    setModalTags(null);
    setModalLoading(true);
    try {
      const payload = await api.public.popularTagsForGif(gif.id, 5);
      setModalTags(payload?.tags || []);
    } catch {
      setModalTags([]);
    } finally {
      setModalLoading(false);
    }
  }

  function closeGifModal() {
    setModalGif(null);
    setModalTags(null);
  }

  function handleTagClick(tag) {
    closeGifModal();
    runTagSearch(tag);
  }

  const handleAddToLibrary = useCallback(async (gifId, tags) => {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) {
      onOpenAuthModal();
      return;
    }
    await action.run(async () => {
      await api.web.updateTags(activeToken, gifId, tags);
      setAddedGifIds(prev => new Set(prev).add(gifId));
    }, 'Гифка добавлена в вашу библиотеку!');
  }, [tokens, onOpenAuthModal, action]);

  const visibleGifs = results?.data || popularGifs?.gifs;

  return (
    <div className="pageLayout">
      <section className="pageIntro">
        <div>
          <span className="eyebrow">Публичная библиотека</span>
          <h2>Что сейчас в тренде</h2>
          <p>Подборка популярных гифок. Пользуйтесь поиском по тегам для быстрой навигации.</p>
          {DEV_MODE && (
          <p>
            Данные кешируются автоматически.
            Для тестов обновление кэша и пересчет популярных данных происходит через 30с.
            В отличие от кеша пользователя этот кэш не инвалидируется автоматически.<br />
            Время кеширования настраивается у каждого сервиса отдельно. 
            Время перерасчета популярных тегов и гифок можно настроить в lifespan.<br />
            Эта надпись видна только при использовании DEV_MODE.
          </p>
        )}
        </div>
      </section>

      <div className="layoutWithSidebar">
        <aside className="panel statPanel">
          <h3>Популярные теги</h3>
          {popularTags?.tags?.length > 0 ? (
            <div className="chips noPad">
              {popularTags.tags.map((tag) => (
                <button key={tag} type="button" className="chip chipButton" onClick={() => runTagSearch(tag)}>
                  #{tag}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">Тегов пока нет.</p>
          )}
        </aside>

        <div className="mainContentArea">
          <form className="panel searchPanel" onSubmit={submitSearch}>
            <label className="fullWidthLabel">
              Поиск по тегам
              <TagInput
                tags={search.tags}
                onChange={(newTags) => setSearch({ ...search, tags: newTags })}
                placeholder="смешное, коты, реакция..."
              />
            </label>

            <div className="searchControlsRow">
              <label className="sortingLabel">
                <span>Сортировка:</span>
                <select value={search.sorting} onChange={(event) => setSearch({ ...search, sorting: event.target.value })}>
                  <option value="desc">Сначала новые</option>
                  <option value="asc">Сначала старые</option>
                </select>
              </label>
              <SubmitButton loading={action.loading} icon={Search}>Искать</SubmitButton>
            </div>
          </form>

          <Status action={action} />
          <GifGrid gifs={visibleGifs} onGifClick={openGifModal} />

          {results?.pagination?.has_next && (
            <button className="secondaryButton loadMoreButton" type="button" onClick={loadMoreResults} disabled={action.loading}>
              {action.loading ? 'Загружаю...' : 'Показать ещё'}
            </button>
          )}
        </div>
      </div>

      <GifModal
        gif={modalGif}
        tags={modalTags}
        loading={modalLoading}
        tagsEmptyHint="Популярных тегов пока нет."
        onClose={closeGifModal}
        onTagClick={handleTagClick}
        onAddToLibrary={handleAddToLibrary}
        isAdded={addedGifIds.has(modalGif?.id)}
      />
    </div>
  );
}

function UserPage({ tokens, profile, setProfile, clearTokens, userExtra }) {
  const [filters, setFilters] = useState(defaultLibrary);
  const [library, setLibrary] = useState(null);
  const [modalGif, setModalGif] = useState(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);

  const action = useAsyncAction();
  const authenticated = Boolean(tokens?.access_token);

  async function fetchDashboardData() {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;

    const [me, count, tags, gifs] = await Promise.all([
      api.web.me(activeToken),
      api.web.count(activeToken),
      api.web.tags(activeToken),
      api.web.gifs(activeToken, toQuery(filters)),
    ]);

    setProfile({ ...userExtra, ...me, gifCount: count, tags });
    setLibrary(gifs);
  }

  async function loadDashboard() {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;
    await action.run(fetchDashboardData);
  }

  async function loadMoreLibrary() {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!library?.pagination?.has_next || !activeToken) return;

    const payload = await action.run(() =>
      api.web.gifs(activeToken, { ...toQuery(filters), cursor: library.pagination.next_cursor }),
    );
    setLibrary((current) => ({
      data: [...(current?.data || []), ...payload.data],
      pagination: payload.pagination,
    }));
  }

  useEffect(() => {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (activeToken) {
      loadDashboard();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated, tokens?.access_token]);

  async function handleUpload(file, tags) {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;
    await api.web.upload(activeToken, file, tags);
    action.setMessage('Файл успешно загружен.');
    fetchDashboardData();
  }

  async function runTagSearch(tag) {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;
    const nextFilters = { ...filters, tags: tag };
    setFilters(nextFilters);
    const payload = await action.run(() => api.web.gifs(activeToken, toQuery(nextFilters)));
    setLibrary(payload);
  }

  async function saveGifTags(gifId, tagsArray) {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;
    await api.web.updateTags(activeToken, gifId, tagsArray);
    setLibrary((current) =>
      current
        ? {
            ...current,
            data: current.data.map((gif) => (gif.id === gifId ? { ...gif, tags: tagsArray } : gif)),
          }
        : current,
    );
    action.setMessage('Теги обновлены.');
  }

  async function removeGifFromLibrary(gifId) {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;
    await api.web.deleteGifs(activeToken, [gifId]);
    setLibrary((current) =>
      current
        ? {
            ...current,
            data: current.data.filter((gif) => gif.id !== gifId),
          }
        : current,
    );
    setProfile((current) => (current ? { ...current, gifCount: Math.max(0, (current.gifCount || 1) - 1) } : current));
    action.setMessage('Гифка удалена.');
  }

  function toggleSelectGif(gifId) {
    setSelectedIds((prev) =>
      prev.includes(gifId) ? prev.filter((id) => id !== gifId) : [...prev, gifId],
    );
  }

  function toggleSelectAll() {
    if (!library?.data) return;
    if (selectedIds.length === library.data.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(library.data.map((g) => g.id));
    }
  }

  async function handleBatchDelete() {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (selectedIds.length === 0 || !activeToken) return;
    if (!window.confirm(`Вы уверены, что хотите удалить выбранные гифки (${selectedIds.length} шт.)?`)) {
      return;
    }

    await action.run(async () => {
      await api.web.deleteGifs(activeToken, selectedIds);
      setLibrary((current) =>
        current
          ? {
              ...current,
              data: current.data.filter((gif) => !selectedIds.includes(gif.id)),
            }
          : current,
      );
      setProfile((current) =>
        current
          ? { ...current, gifCount: Math.max(0, (current.gifCount || 0) - selectedIds.length) }
          : current,
      );
      setSelectedIds([]);
      setIsSelectMode(false);
    }, `Успешно удалено гифок: ${selectedIds.length}`);
  }

  async function handleDeleteAccount() {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) return;
    if (!window.confirm('Вы уверены, что хотите НАВСЕГДА удалить свой аккаунт и все гифки?')) {
      return;
    }
    await action.run(() => api.web.deleteMe(activeToken), 'Аккаунт удален.');
    clearTokens();
    setProfile(null);
    setLibrary(null);
  }

  const displayName = DEV_MODE
    ? `ID: ${profile?.id || profile?.telegram_id || '---'}`
    : (profile?.first_name || (profile?.username ? `@${profile.username}` : 'Моя библиотека'));

  const userTags = Array.isArray(profile?.tags) ? profile.tags : profile?.tags?.tags || [];

  return (
    <div className="pageLayout">
      <section className="pageIntro">
        <div className="userHeaderTitle">
          <span className="eyebrow">Личная коллекция</span>
          <h2>{displayName}</h2>
          <p>Загружайте новые файлы, управляйте тегами и сохраняйте любимые GIF.</p>
        </div>
        <div className="buttonRow">
          <button className="dangerGhost" type="button" onClick={handleDeleteAccount} disabled={!authenticated || action.loading}>
            <Trash2 size={16} />
            Удалить аккаунт
          </button>
        </div>
      </section>

      <div className="layoutWithSidebar">
        <aside className="panel statPanel">
          <h3>Мои теги</h3>
          {userTags.length > 0 ? (
            <div className="chips noPad">
              {userTags.map((tag) => (
                <button key={tag} type="button" className="chip chipButton" onClick={() => runTagSearch(tag)}>
                  #{tag}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">Тегов пока нет.</p>
          )}
        </aside>

        <div className="mainContentArea">
          <form className="panel searchPanel" onSubmit={(event) => { event.preventDefault(); loadDashboard(); }}>
            <label className="fullWidthLabel">
              Фильтр по тегам
              <TagInput
                tags={filters.tags}
                onChange={(newTags) => setFilters({ ...filters, tags: newTags })}
                placeholder="мем, реакция..."
              />
            </label>

            <div className="searchControlsRow userSearchControlsRow">
              <SubmitButton loading={action.loading} icon={Search} disabled={!authenticated}>Искать</SubmitButton>
            </div>
          </form>

          <Status action={action} />

          <div className="libraryHeader">
            <div className="totalCount">
              Всего: <strong>{profile?.gifCount ?? library?.data?.length ?? 0}</strong>
            </div>
            <div className="buttonRow">
              {library?.data?.length > 0 && (
                <button
                  className={`secondaryButton ${isSelectMode ? 'active' : ''}`}
                  type="button"
                  onClick={() => {
                    setIsSelectMode(!isSelectMode);
                    setSelectedIds([]);
                  }}
                >
                  <CheckSquare size={16} />
                  {isSelectMode ? 'Отмена выбора' : 'Выбрать несколько'}
                </button>
              )}
              <button className="button" type="button" onClick={() => setIsUploadOpen(true)}>
                <Plus size={18} />
                Добавить GIF
              </button>
            </div>
          </div>

          {isSelectMode && (
            <div className="batchActionsBar panel">
              <span>Выбрано: <strong>{selectedIds.length}</strong></span>
              <div className="buttonRow">
                <button className="secondaryButton" type="button" onClick={toggleSelectAll}>
                  {selectedIds.length === library?.data?.length ? 'Снять выделение' : 'Выбрать все'}
                </button>
                <button
                  className="button danger"
                  type="button"
                  onClick={handleBatchDelete}
                  disabled={selectedIds.length === 0 || action.loading}
                >
                  <Trash2 size={16} />
                  Удалить выбранные ({selectedIds.length})
                </button>
              </div>
            </div>
          )}

          <GifGrid
            gifs={library?.data}
            onGifClick={setModalGif}
            selectionMode={isSelectMode}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelectGif}
          />

          {library?.pagination?.has_next && (
            <button className="secondaryButton loadMoreButton" type="button" onClick={loadMoreLibrary} disabled={action.loading}>
              {action.loading ? 'Загружаю...' : 'Показать ещё'}
            </button>
          )}
        </div>
      </div>

      <GifModal
        gif={modalGif}
        tags={modalGif?.tags}
        loading={false}
        editable={true}
        onSaveTags={saveGifTags}
        onDelete={removeGifFromLibrary}
        tagsEmptyHint="У этой GIF пока нет тегов."
        onClose={() => setModalGif(null)}
      />

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUpload={handleUpload}
      />
    </div>
  );
}

export default function App() {
  const { tokens, setTokens, clearTokens } = useTokens();
  const [profile, setProfile] = useState(null);
  const [userExtra, setUserExtra] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('gifs_user_extra')) || {};
    } catch {
      return {};
    }
  });

  const [page, setPage] = useState(() => localStorage.getItem('gifs-api-demo.activePage') || 'popular');
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('gifs-api-demo.theme') || 'light');
  const [accent, setAccent] = useState(() => localStorage.getItem('gifs-api-demo.accent') || 'mono');
  
  const profileAction = useAsyncAction();
  const loginAction = useAsyncAction();

  const authenticated = Boolean(tokens?.access_token);

  const navItems = useMemo(
    () => [
      ['popular', 'Популярное', Database],
      ['user', authenticated ? 'Моя библиотека' : 'Войти', authenticated ? Library : User],
    ],
    [authenticated],
  );

  useEffect(() => {
    localStorage.setItem('gifs-api-demo.activePage', page);
  }, [page]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('gifs-api-demo.theme', theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.dataset.accent = accent;
    localStorage.setItem('gifs-api-demo.accent', accent);
  }, [accent]);

  function saveExtraInfo(extra) {
    setUserExtra(extra);
    localStorage.setItem('gifs_user_extra', JSON.stringify(extra));
  }

  async function refreshProfile(token = tokens?.access_token, extraOverride = null) {
    const activeToken = getStoredTokens()?.access_token || token;
    if (!activeToken) return;

    try {
      const [me, count, tags] = await profileAction.run(() =>
        Promise.all([api.web.me(activeToken), api.web.count(activeToken), api.web.tags(activeToken)]),
      );
      const currentExtra = extraOverride || userExtra;
      setProfile({ ...currentExtra, ...me, gifCount: count, tags });
    } catch (err) {
      if (err?.status === 401 || err?.status === 403) {
        handleLogout(false);
      }
    }
  }

  // Загружаем профиль сразу при старте приложения, если пользователь авторизован
  useEffect(() => {
    const activeToken = getStoredTokens()?.access_token || tokens?.access_token;
    if (!activeToken) {
      setProfile(null);
      if (page === 'user') {
        setPage('popular');
      }
    } else if (!profile) {
      refreshProfile(activeToken);
    }
  }, [tokens?.access_token, page]);

  function handleNavClick(id) {
    if (id === 'user' && !authenticated) {
      setIsAuthOpen(true);
      return;
    }
    setPage(id);
  }

  async function handleTelegramLogin(user) {
    const extra = {
      photo_url: user.photo_url,
      username: user.username,
      first_name: user.first_name,
      id: user.id,
      telegram_id: user.id,
    };
    saveExtraInfo(extra);

    const nextTokens = await loginAction.run(() => api.auth.telegram(user));
    setStoredTokens(nextTokens);
    setTokens(nextTokens);
    await refreshProfile(nextTokens.access_token, extra);
    setIsAuthOpen(false);
    setPage('user');
  }

  function handleLoginSuccess() {
    setIsAuthOpen(false);
    setPage('user');
  }

  async function handleLogout(confirm = true) {
    if (confirm && !window.confirm('Вы действительно хотите выйти из аккаунта?')) {
      return;
    }
    if (tokens?.access_token) {
      try {
        await api.auth.logout(tokens.access_token);
      } catch {
        // Игнорируем ошибки при выходе
      }
    }
    clearTokens();
    localStorage.removeItem('gifs_user_extra');
    setUserExtra({});
    setProfile(null);
    setPage('popular');
  }

  return (
    <div className="appShell">
      <header className="topBar">
        <button className="brandButton" type="button" onClick={() => setPage('popular')}>
          <span className="productMark">GIFs API</span>
          <strong>Backend demo</strong>
        </button>
        <nav className="pageNav">
          {navItems.map(([id, label, Icon]) => (
            <button
              className={page === id ? 'navButton active' : 'navButton'}
              type="button"
              key={id}
              onClick={() => handleNavClick(id)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>
        <div className="topBarControls">
          {authenticated && (
            <UserProfileMenu
              profile={profile}
              onLogout={handleLogout}
              devMode={DEV_MODE}
            />
          )}

          <select
            className="accentSelect"
            value={accent}
            onChange={(event) => setAccent(event.target.value)}
            title="Цветовая схема"
          >
            {ACCENT_THEMES.map((item) => (
              <option value={item.id} key={item.id}>{item.label}</option>
            ))}
          </select>

          <button
            className="iconButton squareButton"
            type="button"
            title={theme === 'dark' ? 'Светлая тема' : 'Темная тема'}
            onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      <main>
        <Status action={profileAction} />
        <Status action={loginAction} />
        {page === 'popular' ? (
          <PopularPage tokens={tokens} onOpenAuthModal={() => setIsAuthOpen(true)} />
        ) : (
          <UserPage
            tokens={tokens}
            profile={profile}
            setProfile={setProfile}
            clearTokens={clearTokens}
            userExtra={userExtra}
          />
        )}

        <AuthModal
          isOpen={isAuthOpen}
          onClose={() => setIsAuthOpen(false)}
          setTokens={setTokens}
          refreshProfile={refreshProfile}
          onSuccess={handleLoginSuccess}
          onTelegramLogin={handleTelegramLogin}
          onExtraSave={saveExtraInfo}
        />
      </main>
    </div>
  );
}
