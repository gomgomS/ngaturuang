// Money Management AI - Main JavaScript File

// Global variables
let currentUser = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Money Management AI initialized');
    initializeApp();
});

// Main initialization function
function initializeApp() {
    // Set up event listeners
    setupEventListeners();
    
    // Initialize tooltips and popovers
    initializeBootstrapComponents();
    
    // Load initial data
    loadInitialData();
}

// Setup all event listeners
function setupEventListeners() {
    // Filter auto-submit
    setupFilterAutoSubmit();
    
    // Modal form submissions
    setupModalForms();
    
    // CRUD operations
    setupCRUDOperations();
    
    // Navigation
    setupNavigation();
}

// Initialize Bootstrap components
function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Setup filter auto-submit
function setupFilterAutoSubmit() {
    const filterSelects = document.querySelectorAll('#filterForm select, #filterForm input[type="date"], #filterForm input[type="number"]');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            document.getElementById('filterForm').submit();
        });
    });
}

// Setup modal forms
function setupModalForms() {
    // Add Transaction Modal
    const addTransactionForm = document.getElementById('addTransactionForm');
    if (addTransactionForm) {
        addTransactionForm.addEventListener('submit', handleAddTransaction);
    }
    
    // Edit Transaction Modal
    const editTransactionForm = document.getElementById('editTransactionForm');
    if (editTransactionForm) {
        editTransactionForm.addEventListener('submit', handleEditTransaction);
    }
    
    // Add/Edit Scope Modals
    const addScopeForm = document.getElementById('addScopeForm');
    const editScopeForm = document.getElementById('editScopeForm');
    if (addScopeForm) addScopeForm.addEventListener('submit', handleAddScope);
    if (editScopeForm) editScopeForm.addEventListener('submit', handleEditScope);
    
    // Add/Edit Saving Space Modals
    const addSavingSpaceForm = document.getElementById('addSavingSpaceForm');
    const editSavingSpaceForm = document.getElementById('editSavingSpaceForm');
    if (addSavingSpaceForm) addSavingSpaceForm.addEventListener('submit', handleAddSavingSpace);
    if (editSavingSpaceForm) editSavingSpaceForm.addEventListener('submit', handleEditSavingSpace);
    
    // Add/Edit Category Modals
    const addCategoryForm = document.getElementById('addCategoryForm');
    const editCategoryForm = document.getElementById('editCategoryForm');
    if (addCategoryForm) addCategoryForm.addEventListener('submit', handleAddCategory);
    if (editCategoryForm) editCategoryForm.addEventListener('submit', handleEditCategory);
}

// Setup CRUD operations
function setupCRUDOperations() {
    // Delete buttons
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-delete')) {
            e.preventDefault();
            const itemType = e.target.dataset.type;
            const itemId = e.target.dataset.id;
            handleDelete(itemType, itemId);
        }
        
        // Edit buttons
        if (e.target.classList.contains('btn-edit')) {
  e.preventDefault();
            const itemType = e.target.dataset.type;
            const itemId = e.target.dataset.id;
            handleEdit(itemType, itemId);
        }
    });
}

// Setup navigation
function setupNavigation() {
    // Mobile menu toggle
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.navbar') && navbarCollapse && navbarCollapse.classList.contains('show')) {
            navbarCollapse.classList.remove('show');
        }
    });
}

// Load initial data
async function loadInitialData() {
    try {
        // Load user info
        await loadUserInfo();
        
        // Load master data if on settings page
        if (window.location.pathname === '/settings') {
            await loadMasterData();
        }
        
        // Load transactions if on transactions page
        if (window.location.pathname === '/transactions') {
            await loadTransactions();
        }
        
        // Load dashboard data if on dashboard page
        if (window.location.pathname === '/dashboard') {
            await loadDashboardData();
        }
        
    } catch (error) {
        console.error('Error loading initial data:', error);
        showAlert('Error loading data. Please refresh the page.', 'danger');
    }
}

// Load user info
async function loadUserInfo() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            currentUser = await response.json();
            updateUserInterface();
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Update user interface based on user data
function updateUserInterface() {
    const userDropdown = document.querySelector('.dropdown-toggle');
    if (userDropdown && currentUser) {
        userDropdown.innerHTML = `<i class="fas fa-user me-1"></i>${currentUser.username || 'Demo User'}`;
    }
}

// Load master data for settings page
async function loadMasterData() {
    try {
        const [scopesRes, walletsRes, categoriesRes] = await Promise.all([
            fetch('/api/scopes/'),
            fetch('/api/wallets/'),
            fetch('/api/categories/')
        ]);
        
        if (scopesRes.ok && walletsRes.ok && categoriesRes.ok) {
            const scopes = await scopesRes.json();
            const wallets = await walletsRes.json();
            const categories = await categoriesRes.json();
            
            updateMasterDataDisplay(scopes, wallets, categories);
        }
    } catch (error) {
        console.error('Error loading master data:', error);
    }
}

// Update master data display
function updateMasterDataDisplay(scopes, wallets, categories) {
    // Update scopes display
    updateScopesDisplay(scopes);
    
    // Update wallets display
    updateWalletsDisplay(wallets);
    
    // Update categories display
    updateCategoriesDisplay(categories);
}

// Update scopes display
function updateScopesDisplay(scopes) {
    const scopesContainer = document.getElementById('scopesContainer');
    if (!scopesContainer) return;
    
    if (scopes.length === 0) {
        scopesContainer.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-folder fa-3x text-muted mb-3"></i>
                <h6 class="text-muted">No scopes created yet</h6>
                <p class="text-muted small">Create your first scope to organize your finances</p>
            </div>
        `;
        return;
    }
    
    scopesContainer.innerHTML = scopes.map(scope => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-1">${scope.name}</h6>
                <small class="text-muted">${scope.description || 'No description'}</small>
            </div>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary btn-edit" data-type="scope" data-id="${scope._id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger btn-delete" data-type="scope" data-id="${scope._id}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// Update wallets display
function updateWalletsDisplay(wallets) {
    const walletsContainer = document.getElementById('walletsContainer');
    if (!walletsContainer) return;
    
    if (wallets.length === 0) {
        walletsContainer.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-piggy-bank fa-3x text-muted mb-3"></i>
                <h6 class="text-muted">No saving spaces created yet</h6>
                <p class="text-muted small">Create your first saving space to track your money</p>
            </div>
        `;
        return;
    }
    
    walletsContainer.innerHTML = wallets.map(wallet => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-1">${wallet.name}</h6>
                <small class="text-muted">Type: ${wallet.type || 'bank'}</small>
            </div>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary btn-edit" data-type="wallet" data-id="${wallet._id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger btn-delete" data-type="wallet" data-id="${wallet._id}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// Update categories display
function updateCategoriesDisplay(categories) {
    const categoriesContainer = document.getElementById('categoriesContainer');
    if (!categoriesContainer) return;
    
    if (categories.length === 0) {
        categoriesContainer.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-tags fa-3x text-muted mb-3"></i>
                <h6 class="text-muted">No categories created yet</h6>
                <p class="text-muted small">Create your first category to organize transactions</p>
            </div>
        `;
        return;
    }
    
    categoriesContainer.innerHTML = categories.map(category => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-1">${category.name}</h6>
                <small class="text-muted">${category.description || 'No description'}</small>
            </div>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary btn-edit" data-type="category" data-id="${category._id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger btn-delete" data-type="category" data-id="${category._id}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// Load transactions
async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions/');
        if (response.ok) {
            const transactions = await response.json();
            updateTransactionsDisplay(transactions);
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// Update transactions display
function updateTransactionsDisplay(transactions) {
    const transactionsContainer = document.getElementById('transactionsContainer');
    if (!transactionsContainer) return;
    
    if (transactions.length === 0) {
        transactionsContainer.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-receipt fa-3x text-muted mb-3"></i>
                <h6 class="text-muted">No transactions found</h6>
                <p class="text-muted small">Create your first transaction to get started</p>
            </div>
        `;
        return;
    }
    
    // This will be handled by the server-side rendering
    // Just update any dynamic elements if needed
}

// Load dashboard data
async function loadDashboardData() {
    try {
        // Dashboard data is loaded server-side
        // Just update any dynamic elements if needed
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Handle add transaction
async function handleAddTransaction(e) {
  e.preventDefault();
    
  const form = e.target;
    const formData = new FormData(form);
    
  const payload = {
        amount: parseFloat(formData.get('amount')),
        type: formData.get('type'),
        category_id: formData.get('category_id') || null,
        wallet_id: formData.get('wallet_id') || null,
        scope_id: formData.get('scope_id') || null,
        tags: formData.get('tags') ? formData.get('tags').split(',').map(t => t.trim()).filter(Boolean) : [],
        note: formData.get('note') || '',
        timestamp: formData.get('timestamp') ? Math.floor(new Date(formData.get('timestamp')).getTime() / 1000) : Math.floor(Date.now() / 1000)
    };
    
    try {
        const response = await fetch('/api/transactions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Transaction added successfully!', 'success');
  form.reset();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addTransactionModal'));
            if (modal) modal.hide();
            
            // Reload page to show new transaction
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to add transaction', 'danger');
        }
    } catch (error) {
        console.error('Error adding transaction:', error);
        showAlert('Error adding transaction. Please try again.', 'danger');
    }
}

// Handle edit transaction
async function handleEditTransaction(e) {
  e.preventDefault();
    
  const form = e.target;
    const formData = new FormData(form);
    const transactionId = formData.get('transaction_id');
    
  const payload = {
        amount: parseFloat(formData.get('amount')),
        type: formData.get('type'),
        category_id: formData.get('category_id') || null,
        wallet_id: formData.get('wallet_id') || null,
        scope_id: formData.get('scope_id') || null,
        tags: formData.get('tags') ? formData.get('tags').split(',').map(t => t.trim()).filter(Boolean) : [],
        note: formData.get('note') || '',
        timestamp: formData.get('timestamp') ? Math.floor(new Date(formData.get('timestamp')).getTime() / 1000) : Math.floor(Date.now() / 1000)
    };
    
    try {
        const response = await fetch(`/api/transactions/${transactionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Transaction updated successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editTransactionModal'));
            if (modal) modal.hide();
            
            // Reload page to show updated transaction
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to update transaction', 'danger');
        }
    } catch (error) {
        console.error('Error updating transaction:', error);
        showAlert('Error updating transaction. Please try again.', 'danger');
    }
}

// Handle add scope
async function handleAddScope(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    
    const payload = {
        name: formData.get('name'),
        description: formData.get('description') || ''
    };
    
    try {
        const response = await fetch('/api/scopes/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Scope added successfully!', 'success');
            form.reset();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('scopeModal'));
            if (modal) modal.hide();
            
            // Reload page to show new scope
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to add scope', 'danger');
        }
    } catch (error) {
        console.error('Error adding scope:', error);
        showAlert('Error adding scope. Please try again.', 'danger');
    }
}

// Handle edit scope
async function handleEditScope(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const scopeId = formData.get('scope_id');
    
    const payload = {
        name: formData.get('name'),
        description: formData.get('description') || ''
    };
    
    try {
        const response = await fetch(`/api/scopes/${scopeId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Scope updated successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editScopeModal'));
            if (modal) modal.hide();
            
            // Reload page to show updated scope
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to update scope', 'danger');
        }
    } catch (error) {
        console.error('Error updating scope:', error);
        showAlert('Error updating scope. Please try again.', 'danger');
    }
}

// Handle add saving space
async function handleAddSavingSpace(e) {
  e.preventDefault();
    
  const form = e.target;
    const formData = new FormData(form);
    
  const payload = {
        name: formData.get('name'),
        type: formData.get('type') || 'bank'
    };
    
    try {
        const response = await fetch('/api/wallets/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Saving space added successfully!', 'success');
            form.reset();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('savingSpaceModal'));
            if (modal) modal.hide();
            
            // Reload page to show new saving space
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to add saving space', 'danger');
        }
    } catch (error) {
        console.error('Error adding saving space:', error);
        showAlert('Error adding saving space. Please try again.', 'danger');
    }
}

// Handle edit saving space
async function handleEditSavingSpace(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const walletId = formData.get('wallet_id');
    
    const payload = {
        name: formData.get('name'),
        type: formData.get('type') || 'bank'
    };
    
    try {
        const response = await fetch(`/api/wallets/${walletId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Saving space updated successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editSavingSpaceModal'));
            if (modal) modal.hide();
            
            // Reload page to show updated saving space
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to update saving space', 'danger');
        }
    } catch (error) {
        console.error('Error updating saving space:', error);
        showAlert('Error updating saving space. Please try again.', 'danger');
    }
}

// Handle add category
async function handleAddCategory(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    
    const payload = {
        name: formData.get('name'),
        description: formData.get('description') || ''
    };
    
    try {
        const response = await fetch('/api/categories/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Category added successfully!', 'success');
            form.reset();
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('categoryModal'));
            if (modal) modal.hide();
            
            // Reload page to show new category
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to add category', 'danger');
        }
    } catch (error) {
        console.error('Error adding category:', error);
        showAlert('Error adding category. Please try again.', 'danger');
    }
}

// Handle edit category
async function handleEditCategory(e) {
  e.preventDefault();
    
  const form = e.target;
    const formData = new FormData(form);
    const categoryId = formData.get('category_id');
    
  const payload = {
        name: formData.get('name'),
        description: formData.get('description') || ''
    };
    
    try {
        const response = await fetch(`/api/categories/${categoryId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            showAlert('Category updated successfully!', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editCategoryModal'));
            if (modal) modal.hide();
            
            // Reload page to show updated category
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || 'Failed to update category', 'danger');
        }
    } catch (error) {
        console.error('Error updating category:', error);
        showAlert('Error updating category. Please try again.', 'danger');
    }
}

// Handle edit operations
async function handleEdit(itemType, itemId) {
    try {
        let response;
        let data;
        
        switch (itemType) {
            case 'scope':
                response = await fetch(`/api/scopes/${itemId}`);
                data = await response.json();
                populateEditScopeModal(data);
                break;
            case 'wallet':
                response = await fetch(`/api/wallets/${itemId}`);
                data = await response.json();
                populateEditSavingSpaceModal(data);
                break;
            case 'category':
                response = await fetch(`/api/categories/${itemId}`);
                data = await response.json();
                populateEditCategoryModal(data);
                break;
            case 'transaction':
                response = await fetch(`/api/transactions/${itemId}`);
                data = await response.json();
                populateEditTransactionModal(data);
                break;
        }
        
        // Show edit modal
        const modalId = `edit${itemType.charAt(0).toUpperCase() + itemType.slice(1)}Modal`;
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();
        
    } catch (error) {
        console.error(`Error loading ${itemType} for edit:`, error);
        showAlert(`Error loading ${itemType} for edit. Please try again.`, 'danger');
    }
}

// Handle delete operations
async function handleDelete(itemType, itemId) {
    if (!confirm(`Are you sure you want to delete this ${itemType}?`)) {
        return;
    }
    
    try {
        let response;
        
        switch (itemType) {
            case 'scope':
                response = await fetch(`/api/scopes/${itemId}`, { method: 'DELETE' });
                break;
            case 'wallet':
                response = await fetch(`/api/wallets/${itemId}`, { method: 'DELETE' });
                break;
            case 'category':
                response = await fetch(`/api/categories/${itemId}`, { method: 'DELETE' });
                break;
            case 'transaction':
                response = await fetch(`/api/transactions/${itemId}`, { method: 'DELETE' });
                break;
        }
        
        if (response.ok) {
            showAlert(`${itemType.charAt(0).toUpperCase() + itemType.slice(1)} deleted successfully!`, 'success');
            // Reload page to reflect changes
            window.location.reload();
        } else {
            const error = await response.json();
            showAlert(error.error || `Failed to delete ${itemType}`, 'danger');
        }
    } catch (error) {
        console.error(`Error deleting ${itemType}:`, error);
        showAlert(`Error deleting ${itemType}. Please try again.`, 'danger');
    }
}

// Populate edit modals
function populateEditScopeModal(scope) {
    const form = document.getElementById('editScopeForm');
    if (form) {
        form.querySelector('[name="scope_id"]').value = scope._id;
        form.querySelector('[name="name"]').value = scope.name;
        form.querySelector('[name="description"]').value = scope.description || '';
    }
}

function populateEditSavingSpaceModal(wallet) {
    const form = document.getElementById('editSavingSpaceForm');
    if (form) {
        form.querySelector('[name="wallet_id"]').value = wallet._id;
        form.querySelector('[name="name"]').value = wallet.name;
        form.querySelector('[name="type"]').value = wallet.type || 'bank';
    }
}

function populateEditCategoryModal(category) {
    const form = document.getElementById('editCategoryForm');
    if (form) {
        form.querySelector('[name="category_id"]').value = category._id;
        form.querySelector('[name="name"]').value = category.name;
        form.querySelector('[name="description"]').value = category.description || '';
    }
}

function populateEditTransactionModal(transaction) {
    const form = document.getElementById('editTransactionForm');
    if (form) {
        form.querySelector('[name="transaction_id"]').value = transaction._id;
        form.querySelector('[name="amount"]').value = transaction.amount;
        form.querySelector('[name="type"]').value = transaction.type;
        form.querySelector('[name="category_id"]').value = transaction.category_id || '';
        form.querySelector('[name="wallet_id"]').value = transaction.wallet_id || '';
        form.querySelector('[name="scope_id"]').value = transaction.scope_id || '';
        form.querySelector('[name="tags"]').value = Array.isArray(transaction.tags) ? transaction.tags.join(', ') : '';
        form.querySelector('[name="note"]').value = transaction.note || '';
        
        // Convert timestamp to datetime-local format (using local timezone)
        if (transaction.timestamp) {
            const date = new Date(transaction.timestamp * 1000);
            // Format as YYYY-MM-DDTHH:MM using local timezone
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            const localDateTime = `${year}-${month}-${day}T${hours}:${minutes}`;
            form.querySelector('[name="timestamp"]').value = localDateTime;
        }
    }
}

// Show alert message
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(amount);
}

function formatDate(timestamp) {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// AI Advisor functionality
function initializeAIAdvisor() {
    // This function can be called from the AI Advisor page
    console.log('🤖 AI Advisor initialized');
}

// Export functions for global access
window.MoneyManagementAI = {
    showAlert,
    formatCurrency,
    formatDate,
    handleEdit,
    handleDelete,
    initializeAIAdvisor
};


