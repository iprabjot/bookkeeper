/**
 * Reusable File Upload Component
 * Provides consistent file upload UI with file selection display, progress tracking, and loading states
 */

class FileUploadComponent {
    constructor(config) {
        this.config = {
            containerId: config.containerId,
            accept: config.accept || '*',
            multiple: config.multiple !== false,
            onUpload: config.onUpload, // Function that takes file(s) and returns Promise
            uploadText: config.uploadText || 'Upload Files',
            dragText: config.dragText || 'Click to select or drag & drop files',
            helpText: config.helpText || 'You can select multiple files at once',
            maxFiles: config.maxFiles || null,
            ...config
        };
        
        this.selectedFiles = [];
        this.isUploading = false;
        this.container = null;
        this.pollingInterval = null;
        this.uploadStatuses = new Map(); // Map<fileIndex, {status: string, errorMessage: string, uploadId: number}>
        this.listenersAttached = false; // Track if listeners are already attached
        this.init();
    }

    init() {
        this.container = document.getElementById(this.config.containerId);
        if (!this.container) {
            console.error(`Container with id "${this.config.containerId}" not found`);
            return;
        }

        this.render();
        // Attach listeners after a brief delay to ensure DOM is ready
        setTimeout(() => {
            this.attachEventListeners();
        }, 100);
    }

    render() {
        this.container.innerHTML = `
            <div class="bg-white rounded-lg shadow-md border border-gray-200 p-6 mb-6">
                <h3 class="text-xl font-bold text-gray-900 mb-6 flex items-center">
                    <i class="fas fa-cloud-upload-alt text-blue-600 mr-3"></i>
                    ${this.config.uploadText}
                </h3>
                
                <!-- Upload Area -->
                <div class="upload-area relative" id="${this.config.containerId}-upload-area">
                    <input 
                        type="file" 
                        id="${this.config.containerId}-file-input" 
                        accept="${this.config.accept}" 
                        ${this.config.multiple ? 'multiple' : ''}
                        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; z-index: 10;"
                    >
                    <div class="text-center py-8" style="position: relative; z-index: 1; pointer-events: none;">
                        <div class="mb-6">
                            <i class="fas fa-cloud-upload-alt text-6xl text-blue-400 mb-4"></i>
                        </div>
                        <p class="text-lg font-semibold text-gray-700 mb-2">${this.config.dragText}</p>
                        <p class="text-sm text-gray-500 mb-6">${this.config.helpText}</p>
                        <button 
                            type="button" 
                            id="${this.config.containerId}-browse-btn"
                            class="inline-flex items-center px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors duration-200 shadow-sm hover:shadow"
                            style="pointer-events: auto; position: relative; z-index: 20;"
                        >
                            <i class="fas fa-folder-open mr-2"></i>Browse Files
                        </button>
                    </div>
                </div>

                <!-- Selected Files Display -->
                <div id="${this.config.containerId}-files-list" class="hidden mt-6">
                    <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200 p-5 shadow-sm">
                        <div class="flex items-center justify-between mb-4">
                            <h4 class="font-semibold text-gray-900 flex items-center">
                                <i class="fas fa-file-check text-blue-600 mr-2"></i>
                                Selected Files
                            </h4>
                            <button 
                                type="button"
                                id="${this.config.containerId}-clear-btn"
                                class="text-sm font-medium text-red-600 hover:text-red-800 hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors duration-200"
                            >
                                <i class="fas fa-times mr-1"></i>Clear All
                            </button>
                        </div>
                        <div id="${this.config.containerId}-files-list-items" class="space-y-2 max-h-64 overflow-y-auto"></div>
                    </div>
                </div>

                <!-- Upload Button (Hidden until files selected) -->
                <div id="${this.config.containerId}-upload-section" class="hidden mt-6">
                    <div class="flex items-center justify-between bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg p-4 shadow-lg">
                        <div class="flex items-center text-white">
                            <i class="fas fa-upload mr-3 text-xl"></i>
                            <div>
                                <p class="font-semibold">Ready to Upload</p>
                                <p id="${this.config.containerId}-file-count" class="text-sm text-blue-100"></p>
                            </div>
                        </div>
                        <button 
                            id="${this.config.containerId}-upload-btn"
                            type="button"
                            class="bg-white text-blue-600 hover:bg-blue-50 font-semibold px-6 py-3 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                            disabled
                        >
                            <i class="fas fa-paper-plane mr-2"></i>Upload Files
                        </button>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div id="${this.config.containerId}-progress" class="upload-progress hidden mt-4">
                    <div class="flex items-center justify-between mb-2">
                        <span id="${this.config.containerId}-progress-text" class="text-sm font-medium text-gray-700">Processing...</span>
                        <span id="${this.config.containerId}-progress-percent" class="text-sm font-medium text-gray-700">0%</span>
                    </div>
                    <div class="progress-bar">
                        <div id="${this.config.containerId}-progress-fill" class="progress-fill" style="width: 0%"></div>
                    </div>
                </div>

                <!-- Loading Overlay -->
                <div id="${this.config.containerId}-loading-overlay" class="hidden fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
                    <div class="bg-white rounded-lg p-8 max-w-md mx-4 text-center">
                        <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
                        <h3 class="text-xl font-semibold text-gray-900 mb-2">Uploading Files</h3>
                        <p id="${this.config.containerId}-loading-text" class="text-gray-600 mb-4">Please wait while we process your files...</p>
                        <div id="${this.config.containerId}-loading-details" class="text-sm text-gray-500"></div>
                    </div>
                </div>

                <!-- Message Display -->
                <div id="${this.config.containerId}-message" class="mt-4"></div>
            </div>
        `;

    }

    attachEventListeners() {
        // Prevent attaching listeners multiple times
        if (this.listenersAttached) {
            return;
        }

        const fileInput = document.getElementById(`${this.config.containerId}-file-input`);
        const uploadArea = document.getElementById(`${this.config.containerId}-upload-area`);
        const uploadBtn = document.getElementById(`${this.config.containerId}-upload-btn`);
        const clearBtn = document.getElementById(`${this.config.containerId}-clear-btn`);
        const browseBtn = document.getElementById(`${this.config.containerId}-browse-btn`);

        if (!fileInput || !uploadArea) {
            console.error(`Required elements not found for upload component: ${this.config.containerId}`, {
                fileInput: !!fileInput,
                uploadArea: !!uploadArea,
                containerId: this.config.containerId
            });
            return;
        }

        const actualFileInput = fileInput;

        // File input change handler (only attach once)
        actualFileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                this.handleFileSelection(files);
                // Clear the input value to allow selecting the same file again if needed
                e.target.value = '';
            }
        });

        // Browse button click - trigger file input
        if (browseBtn) {
            browseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                actualFileInput.click();
            });
        }

        // Upload button click
        if (uploadBtn) {
            uploadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.startUpload();
            });
        }

        // Clear button click (if it exists)
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.clearFiles();
            });
        }

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.handleFileSelection(files);
            }
        });

        // Mark listeners as attached
        this.listenersAttached = true;
    }

    handleFileSelection(files) {
        if (files.length === 0) return;

        // Filter by accept type if specified
        if (this.config.accept !== '*') {
            const acceptTypes = this.config.accept.split(',').map(t => t.trim());
            files = files.filter(file => {
                const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                return acceptTypes.some(type => type.startsWith('.') ? type === fileExt : file.type.match(type));
            });
        }

        // Check max files limit
        if (this.config.maxFiles && files.length > this.config.maxFiles) {
            this.showMessage(`Maximum ${this.config.maxFiles} files allowed. Only the first ${this.config.maxFiles} will be selected.`, 'warning');
            files = files.slice(0, this.config.maxFiles);
        }

        if (files.length === 0) {
            this.showMessage('No valid files selected.', 'error');
            return;
        }

        // Add to selected files (replace if not multiple)
        if (this.config.multiple) {
            // Check for duplicates by name and size
            const existingFileNames = new Set(this.selectedFiles.map(f => `${f.name}_${f.size}`));
            const newFiles = files.filter(file => {
                const fileKey = `${file.name}_${file.size}`;
                if (existingFileNames.has(fileKey)) {
                    return false; // Skip duplicate
                }
                existingFileNames.add(fileKey);
                return true;
            });
            
            if (newFiles.length < files.length) {
                const duplicateCount = files.length - newFiles.length;
                this.showMessage(`${duplicateCount} duplicate file${duplicateCount > 1 ? 's' : ''} skipped.`, 'warning');
            }
            
            this.selectedFiles = [...this.selectedFiles, ...newFiles];
        } else {
            this.selectedFiles = [files[0]];
        }

        this.updateFilesDisplay();
        this.updateUploadButton();
    }

    updateFilesDisplay() {
        const filesListContainer = document.getElementById(`${this.config.containerId}-files-list`);
        const filesListItems = document.getElementById(`${this.config.containerId}-files-list-items`);
        const fileCount = document.getElementById(`${this.config.containerId}-file-count`);
        const uploadSection = document.getElementById(`${this.config.containerId}-upload-section`);

        if (this.selectedFiles.length === 0) {
            filesListContainer.classList.add('hidden');
            uploadSection.classList.add('hidden');
            return;
        }

        filesListContainer.classList.remove('hidden');
        uploadSection.classList.remove('hidden');
        fileCount.textContent = `${this.selectedFiles.length} file${this.selectedFiles.length > 1 ? 's' : ''} selected`;

        filesListItems.innerHTML = this.selectedFiles.map((file, index) => `
            <div class="flex items-center justify-between bg-white rounded-lg p-3 border border-blue-200 shadow-sm hover:shadow-md transition-shadow duration-200" data-file-index="${index}">
                <div class="flex items-center space-x-3 flex-1 min-w-0">
                    <div class="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center file-status-icon">
                        <i class="fas fa-file-pdf text-blue-600"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-semibold text-gray-900 truncate">${this.escapeHtml(file.name)}</p>
                        <p class="text-xs text-gray-500 mt-0.5">${this.formatFileSize(file.size)}</p>
                    </div>
                </div>
                ${this.config.multiple ? `
                    <button 
                        type="button"
                        data-file-index="${index}"
                        class="remove-file-btn text-red-600 hover:text-red-800 hover:bg-red-50 p-2 rounded-lg ml-2 flex-shrink-0 transition-colors duration-200"
                        title="Remove file"
                    >
                        <i class="fas fa-times"></i>
                    </button>
                ` : ''}
            </div>
        `).join('');

        // Attach event listeners to remove buttons
        if (this.config.multiple) {
            filesListItems.querySelectorAll('.remove-file-btn').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const index = parseInt(btn.getAttribute('data-file-index'));
                    this.removeFile(index);
                });
            });
        }
    }

    updateUploadButton() {
        const uploadBtn = document.getElementById(`${this.config.containerId}-upload-btn`);
        if (this.selectedFiles.length === 0 || this.isUploading) {
            uploadBtn.disabled = true;
        } else {
            uploadBtn.disabled = false;
        }
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFilesDisplay();
        this.updateUploadButton();
    }

    clearFiles() {
        this.selectedFiles = [];
        this.uploadStatuses.clear();
        this.stopStatusPolling();
        document.getElementById(`${this.config.containerId}-file-input`).value = '';
        const filesListContainer = document.getElementById(`${this.config.containerId}-files-list`);
        const uploadSection = document.getElementById(`${this.config.containerId}-upload-section`);
        const messageEl = document.getElementById(`${this.config.containerId}-message`);
        
        if (filesListContainer) filesListContainer.classList.add('hidden');
        if (uploadSection) uploadSection.classList.add('hidden');
        if (messageEl) messageEl.innerHTML = '';
        
        this.updateFilesDisplay();
        this.updateUploadButton();
    }

    async startUpload() {
        if (this.isUploading || this.selectedFiles.length === 0) return;

        if (!this.config.onUpload) {
            console.error('No upload handler provided');
            return;
        }

        this.isUploading = true;
        this.updateUploadButton();
        this.showLoadingOverlay();
        this.showProgress();

        const progressFill = document.getElementById(`${this.config.containerId}-progress-fill`);
        const progressText = document.getElementById(`${this.config.containerId}-progress-text`);
        const progressPercent = document.getElementById(`${this.config.containerId}-progress-percent`);
        const loadingText = document.getElementById(`${this.config.containerId}-loading-text`);
        const loadingDetails = document.getElementById(`${this.config.containerId}-loading-details`);
        const filesListItems = document.getElementById(`${this.config.containerId}-files-list-items`);

        const total = this.selectedFiles.length;
        let processed = 0;
        const results = { success: 0, failed: 0, errors: [] };
        const fileStatuses = new Map(); // Track status of each file

        try {
            // Check if using bulk upload API
            const useBulkUpload = this.config.useBulkUpload !== false && window.uploadMultipleInvoices;
            
            if (useBulkUpload && this.selectedFiles.length > 0) {
                // Use bulk upload API for async processing
                loadingText.textContent = 'Uploading files...';
                loadingDetails.textContent = `Uploading ${total} file${total > 1 ? 's' : ''}...`;
                
                try {
                    // Upload all files at once
                    const uploadResponse = await window.uploadMultipleInvoices(this.selectedFiles);
                    const uploadIds = uploadResponse.upload_ids || [];
                    
                    // Update all files to show uploaded status
                    for (let i = 0; i < this.selectedFiles.length; i++) {
                        const fileElement = filesListItems.querySelector(`[data-file-index="${i}"]`);
                        if (fileElement && i < uploadIds.length) {
                            fileElement.classList.add('opacity-75');
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-clock text-yellow-600"></i>';
                            }
                            // Store upload_id for polling
                            fileElement.setAttribute('data-upload-id', uploadIds[i]);
                        }
                    }
                    
                    results.success = uploadIds.length;
                    results.failed = total - uploadIds.length;
                    
                    // Start polling for status updates
                    this.startStatusPolling(uploadIds);
                    
                } catch (error) {
                    const errorMsg = error.response?.data?.detail || error.message || 'Upload failed';
                    results.failed = total;
                    results.errors.push({ file: 'Bulk upload', error: errorMsg });
                    this.showMessage(`Upload failed: ${errorMsg}`, 'error');
                }
            } else {
                // Fallback to sequential upload (original behavior)
                loadingText.textContent = 'Uploading files...';
                for (let i = 0; i < this.selectedFiles.length; i++) {
                    const file = this.selectedFiles[i];
                    const fileElement = filesListItems.querySelector(`[data-file-index="${i}"]`);
                    
                    loadingDetails.textContent = `Uploading file ${i + 1} of ${total}`;
                    
                    // Update file status to uploading
                    if (fileElement) {
                        fileElement.classList.add('opacity-75');
                        const statusIcon = fileElement.querySelector('.file-status-icon');
                        if (statusIcon) {
                            statusIcon.innerHTML = '<i class="fas fa-spinner fa-spin text-blue-600"></i>';
                        }
                    }

                    try {
                        // Upload file (this should be fast - just save the file)
                        await this.config.onUpload(file);
                        fileStatuses.set(i, 'uploaded');
                        
                        // Update file status to uploaded
                        if (fileElement) {
                            fileElement.classList.remove('opacity-75');
                            fileElement.classList.add('border-green-300', 'bg-green-50');
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-check-circle text-green-600"></i>';
                            }
                        }
                        
                        results.success++;
                    } catch (error) {
                        fileStatuses.set(i, 'failed');
                        const errorMsg = error.response?.data?.detail || error.message || 'Upload failed';
                        results.failed++;
                        results.errors.push({ file: file.name, error: errorMsg });
                        
                        // Update file status to failed
                        if (fileElement) {
                            fileElement.classList.remove('opacity-75');
                            fileElement.classList.add('border-red-300', 'bg-red-50');
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-exclamation-circle text-red-600"></i>';
                            }
                            // Add error message to file element
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'text-xs text-red-600 mt-1';
                            errorDiv.textContent = errorMsg;
                            fileElement.appendChild(errorDiv);
                        }
                        
                        console.error(`Failed to upload ${file.name}:`, error);
                    }

                    processed++;
                    const percent = Math.round((processed / total) * 100);
                    progressFill.style.width = `${percent}%`;
                    progressPercent.textContent = `${percent}%`;
                    progressText.textContent = `Uploaded ${processed}/${total} files...`;
                }
            }

            // Show success/error message (only for sequential uploads, bulk uploads handled by polling)
            if (!useBulkUpload) {
                if (results.success > 0 && results.failed === 0) {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-check-circle mr-2"></i>Successfully uploaded ${results.success} file${results.success > 1 ? 's' : ''}!</div>`,
                        'success',
                        true
                    );
                    // Clear files after success
                    setTimeout(() => {
                        this.clearFiles();
                    }, 2000);
                } else if (results.success > 0 && results.failed > 0) {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-exclamation-triangle mr-2"></i>Uploaded ${results.success} file${results.success > 1 ? 's' : ''}, but ${results.failed} failed. Check errors below.</div>`,
                        'warning',
                        true
                    );
                } else {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-times-circle mr-2"></i>All uploads failed. Please check errors and try again.</div>`,
                        'error',
                        true
                    );
                }
            } else {
                // For bulk uploads, show initial message
                this.showMessage(
                    `<div class="flex items-center"><i class="fas fa-clock mr-2"></i>Files uploaded! Processing in background. Status will update automatically.</div>`,
                    'info',
                    true
                );
            }

            // Show detailed errors if any
            if (results.errors.length > 0) {
                const errorDetails = results.errors.map(e => 
                    `<div class="mt-2 p-2 bg-red-50 border border-red-200 rounded"><strong>${this.escapeHtml(e.file)}:</strong> ${this.escapeHtml(e.error)}</div>`
                ).join('');
                this.showMessage(`<div class="mt-3"><strong>Error Details:</strong>${errorDetails}</div>`, 'error', true);
            }

        } catch (error) {
            this.showMessage(
                `<div class="flex items-center"><i class="fas fa-times-circle mr-2"></i>Upload failed: ${this.escapeHtml(error.message || error)}</div>`,
                'error',
                true
            );
        } finally {
            this.isUploading = false;
            this.hideLoadingOverlay();
            this.updateUploadButton();

            // Hide progress after delay
            setTimeout(() => {
                this.hideProgress();
            }, 3000);
        }
    }

    showLoadingOverlay() {
        document.getElementById(`${this.config.containerId}-loading-overlay`).classList.remove('hidden');
    }

    hideLoadingOverlay() {
        document.getElementById(`${this.config.containerId}-loading-overlay`).classList.add('hidden');
    }

    showProgress() {
        document.getElementById(`${this.config.containerId}-progress`).classList.remove('hidden');
    }

    hideProgress() {
        const progressEl = document.getElementById(`${this.config.containerId}-progress`);
        progressEl.classList.add('hidden');
        const progressFill = document.getElementById(`${this.config.containerId}-progress-fill`);
        progressFill.style.width = '0%';
    }

    showMessage(text, type = 'info', isHtml = false) {
        const messageEl = document.getElementById(`${this.config.containerId}-message`);
        const colors = {
            success: 'bg-green-50 border-green-300 text-green-800',
            error: 'bg-red-50 border-red-300 text-red-800',
            warning: 'bg-yellow-50 border-yellow-300 text-yellow-800',
            info: 'bg-blue-50 border-blue-300 text-blue-800'
        };

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        messageEl.innerHTML = `
            <div class="${colors[type] || colors.info} border-2 px-5 py-4 rounded-xl shadow-sm">
                ${isHtml ? text : `<div class="flex items-center"><i class="fas ${icons[type] || icons.info} mr-2"></i><p>${text}</p></div>`}
            </div>
        `;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    startStatusPolling(uploadIds) {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        const total = uploadIds.length;
        let completedCount = 0;
        let failedCount = 0;

        const progressFill = document.getElementById(`${this.config.containerId}-progress-fill`);
        const progressText = document.getElementById(`${this.config.containerId}-progress-text`);
        const progressPercent = document.getElementById(`${this.config.containerId}-progress-percent`);
        const loadingText = document.getElementById(`${this.config.containerId}-loading-text`);
        const loadingDetails = document.getElementById(`${this.config.containerId}-loading-details`);
        const filesListItems = document.getElementById(`${this.config.containerId}-files-list-items`);

        loadingText.textContent = 'Processing files in background...';

        this.pollingInterval = setInterval(async () => {
            let allCompleted = true;
            let currentCompleted = 0;
            let currentFailed = 0;

            for (let i = 0; i < this.selectedFiles.length; i++) {
                if (i >= uploadIds.length) break;

                const uploadId = uploadIds[i];
                const fileElement = filesListItems.querySelector(`[data-file-index="${i}"]`);
                let fileStatus = this.uploadStatuses.get(i);

                if (!fileStatus) {
                    fileStatus = { status: 'pending', errorMessage: '', uploadId: uploadId };
                    this.uploadStatuses.set(i, fileStatus);
                }

                // Only poll if still pending or processing
                if (fileStatus.status === 'pending' || fileStatus.status === 'processing') {
                    allCompleted = false;
                    try {
                        const statusResponse = await window.getUploadStatus(uploadId);
                        const newStatus = statusResponse.status;
                        const errorMessage = statusResponse.error_message || '';

                        if (newStatus !== fileStatus.status) {
                            fileStatus.status = newStatus;
                            fileStatus.errorMessage = errorMessage;
                            this.uploadStatuses.set(i, fileStatus);

                            // Update UI for this file
                            if (fileElement) {
                                const statusIcon = fileElement.querySelector('.file-status-icon');
                                if (statusIcon) {
                                    if (newStatus === 'completed') {
                                        statusIcon.innerHTML = '<i class="fas fa-check-circle text-green-600"></i>';
                                        fileElement.classList.remove('opacity-75');
                                        fileElement.classList.add('border-green-300', 'bg-green-50');
                                    } else if (newStatus === 'failed') {
                                        statusIcon.innerHTML = '<i class="fas fa-exclamation-circle text-red-600"></i>';
                                        fileElement.classList.remove('opacity-75');
                                        fileElement.classList.add('border-red-300', 'bg-red-50');
                                        if (errorMessage) {
                                            const errorDiv = document.createElement('div');
                                            errorDiv.className = 'text-xs text-red-600 mt-1';
                                            errorDiv.textContent = errorMessage;
                                            fileElement.appendChild(errorDiv);
                                        }
                                    } else if (newStatus === 'processing') {
                                        statusIcon.innerHTML = '<i class="fas fa-spinner fa-spin text-blue-600"></i>';
                                    }
                                }
                            }
                        }
                    } catch (error) {
                        console.error(`Failed to get status for upload ID ${uploadId}:`, error);
                        fileStatus.status = 'failed';
                        fileStatus.errorMessage = error.message || 'Failed to fetch status';
                        this.uploadStatuses.set(i, fileStatus);
                        if (fileElement) {
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-exclamation-circle text-red-600"></i>';
                            }
                        }
                    }
                }

                // Count completed/failed
                if (fileStatus.status === 'completed') {
                    currentCompleted++;
                } else if (fileStatus.status === 'failed') {
                    currentFailed++;
                }
            }

            // Update progress
            const totalProcessed = currentCompleted + currentFailed;
            const percent = total > 0 ? Math.round((totalProcessed / total) * 100) : 0;
            if (progressFill) progressFill.style.width = `${percent}%`;
            if (progressPercent) progressPercent.textContent = `${percent}%`;
            if (progressText) {
                progressText.textContent = `Processed ${totalProcessed}/${total} files (${currentCompleted} completed, ${currentFailed} failed)...`;
            }
            if (loadingDetails) {
                loadingDetails.textContent = `Processed ${totalProcessed} of ${total} files`;
            }

            // Stop polling if all files are completed or failed
            if (allCompleted || totalProcessed === total) {
                this.stopStatusPolling();
                this.hideLoadingOverlay();
                this.hideProgress();
                this.isUploading = false;
                this.updateUploadButton();

                if (currentFailed === 0) {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-check-circle mr-2"></i>All ${currentCompleted} file${currentCompleted > 1 ? 's' : ''} processed successfully!</div>`,
                        'success',
                        true
                    );
                    setTimeout(() => this.clearFiles(), 2000);
                } else {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-info-circle mr-2"></i>Processing complete. ${currentCompleted} succeeded, ${currentFailed} failed.</div>`,
                        currentCompleted > 0 ? 'warning' : 'error',
                        true
                    );
                }

                // Trigger onComplete callback
                if (this.config.onComplete) {
                    this.config.onComplete();
                }
            }
        }, 3000); // Poll every 3 seconds
    }

    stopStatusPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
}

