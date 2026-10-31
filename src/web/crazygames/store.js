// Async SDK transport only. PortalShop owns configuration, pagination,
// reconciliation, pending persistence, retry policy and all entitlements.
function WurmAttachStore(p) {
  let busy = false, result = '';
  p.storeGeneration = 0;
  p.storeProfileReady = false;
  p.storeAuthenticated = false;
  p.userId = '';
  function publicId(profile) { return profile && typeof profile.__dangerousUserId === 'string' ? profile.__dangerousUserId : ''; }
  p.storeReset = function(profile) {
    ++p.storeGeneration;
    p.storeProfileReady = true;
    // Official SDK v3 public ID is an account scope, never a server auth
    // credential. Authentication/payment remains owned by SDK.user/store.
    p.userId = publicId(profile);
    p.storeAuthenticated = !!profile && p.userId.length > 0;
    result = ''; // busy stays locked until the old SDK promise settles
  };
  function available() {
    try { return p.sdkActive && p.sdk.store.isAvailable === true; } catch (_) { return false; }
  }
  function readable() {
    try { return !!p.sdkActive && typeof p.sdk.store.getCatalogItems === 'function' && typeof p.sdk.store.getPlayerInventory === 'function'; } catch (_) { return false; }
  }
  p.storeRead = function(name) {
    if (name === 'config') {
      try { return JSON.stringify(window.WurmPortalStoreConfig || {version:1,sandbox:false,products:[]}); } catch (_) { return ''; }
    }
    if (name === 'result') return result;
    if (name !== 'session') return '';
    return JSON.stringify({active:!!p.sdkActive,readable:readable(),available:!!available(),ready:p.storeProfileReady,
      authenticated:p.storeAuthenticated,userId:p.userId,generation:p.storeGeneration,busy});
  };
  p.storeRequest = function(text) {
    let c;
    try { c = JSON.parse(text); } catch (_) { return false; }
    if (busy || !readable() || !p.storeProfileReady || c.generation !== p.storeGeneration ||
        c.account !== (p.storeAuthenticated ? p.userId : '') ||
        !Number.isSafeInteger(c.id) || !Number.isSafeInteger(c.epoch) ||
        !Number.isSafeInteger(c.offset) || c.offset < 0 || c.offset > 256 ||
        typeof c.sandbox !== 'boolean' || (c.sandbox && p.sdk.environment !== 'local') ||
        !['catalog','inventory','buy'].includes(c.op) ||
        (c.op !== 'catalog' && !p.storeAuthenticated) || (c.op === 'buy' && !available()) ||
        (c.op === 'buy' && (typeof c.purchaseId !== 'string' || !c.purchaseId || c.purchaseId.length > 128))) return false;
    busy = true; result = '';
    const generation = p.storeGeneration, account = p.userId, sdk = p.sdk;
    function current() { return generation === p.storeGeneration && account === p.userId && sdk === p.sdk && p.sdkActive; }
    Promise.resolve().then(async function() {
      if (!current()) throw {code:'accountChanged'};
      // The native checkout preflight always starts at catalog offset zero.
      // Re-read SDK auth before requesting that personalized catalog. A
      // changed identity invalidates this operation before any checkout.
      if (c.op === 'catalog' && c.offset === 0 && p.accountAvailable) {
        const profile = await sdk.user.getUser();
        if (!current()) throw {code:'accountChanged'};
        if (publicId(profile) !== account || (!!profile && !!publicId(profile)) !== p.storeAuthenticated) {
          p.storeReset(profile);
          throw {code:'accountChanged'};
        }
      }
      sdk.store.setSandbox(c.sandbox);
      if (c.op === 'catalog') return sdk.store.getCatalogItems({limit:50,offset:c.offset});
      if (c.op === 'inventory') return sdk.store.getPlayerInventory({limit:50,offset:c.offset});
      return sdk.store.buyItem(c.purchaseId);
    }).then(function(data) {
      if (current()) {
        // Bounded serialization; oversized pages fail closed in native code.
        const out = JSON.stringify({id:c.id,epoch:c.epoch,generation,ok:true,data});
        result = out.length <= 1049088 ? out : JSON.stringify({id:c.id,epoch:c.epoch,generation,ok:false,code:'oversize'});
      }
    }).catch(function(error) {
      if (current()) result = JSON.stringify({id:c.id,epoch:c.epoch,generation,ok:false,
        code:error && error.code === 'purchaseCancelled' ? 'purchaseCancelled' : 'sdkError'});
    }).finally(function() { busy = false; });
    return true;
  };
}
