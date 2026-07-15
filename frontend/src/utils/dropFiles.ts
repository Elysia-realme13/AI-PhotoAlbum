/** 拖拽上传的文件提取工具：支持文件与文件夹（递归子目录），过滤出图片文件 */

/** 允许的图片扩展名（HEIC 等文件的 MIME type 可能为空，需按扩展名兜底） */
const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif', 'bmp', 'tiff']

/** 判断一个文件是否为图片 */
function isImageFile(file: File): boolean {
  if (file.type.startsWith('image/')) return true
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  return IMAGE_EXTENSIONS.includes(ext)
}

/** 将 FileEntry 转为 File */
function entryToFile(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject)
  })
}

/** 读取目录下的一批条目（readEntries 一次最多返回约 100 条，需循环直到返回空数组） */
function readAllEntries(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  return new Promise((resolve, reject) => {
    const all: FileSystemEntry[] = []
    const readBatch = () => {
      reader.readEntries((entries) => {
        if (entries.length === 0) {
          resolve(all)
        } else {
          all.push(...entries)
          readBatch()
        }
      }, reject)
    }
    readBatch()
  })
}

/** 递归遍历一个条目（文件或目录），收集其中的所有文件 */
async function collectFilesFromEntry(entry: FileSystemEntry, files: File[]): Promise<void> {
  if (entry.isFile) {
    const file = await entryToFile(entry as FileSystemFileEntry)
    files.push(file)
  } else if (entry.isDirectory) {
    const reader = (entry as FileSystemDirectoryEntry).createReader()
    const entries = await readAllEntries(reader)
    for (const child of entries) {
      await collectFilesFromEntry(child, files)
    }
  }
}

export interface ExtractResult {
  /** 收集到的图片文件 */
  images: File[]
  /** 被跳过的非图片文件数量 */
  skipped: number
}

/**
 * 从拖拽的 DataTransfer 中提取图片文件。
 * 支持文件与文件夹（递归所有子目录），非图片文件被跳过并计数。
 */
export async function extractImagesFromDrop(dt: DataTransfer): Promise<ExtractResult> {
  const allFiles: File[] = []

  // 优先使用 entry API 以支持文件夹递归
  const items = dt.items
  const canUseEntries =
    items &&
    items.length > 0 &&
    typeof (items[0] as any).webkitGetAsEntry === 'function'

  if (canUseEntries) {
    const entries: FileSystemEntry[] = []
    for (let i = 0; i < items.length; i++) {
      const entry = (items[i] as any).webkitGetAsEntry() as FileSystemEntry | null
      if (entry) entries.push(entry)
    }
    if (entries.length > 0) {
      for (const entry of entries) {
        await collectFilesFromEntry(entry, allFiles)
      }
    } else {
      // 拿不到 entry 时回退到 files
      allFiles.push(...Array.from(dt.files))
    }
  } else {
    // 浏览器不支持 entry API，回退到平铺的 files
    allFiles.push(...Array.from(dt.files))
  }

  const images: File[] = []
  let skipped = 0
  for (const file of allFiles) {
    if (isImageFile(file)) {
      images.push(file)
    } else {
      skipped++
    }
  }

  return { images, skipped }
}
