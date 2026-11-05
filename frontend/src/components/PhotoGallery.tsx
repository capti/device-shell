/** Галерея фотографий устройства: превью, просмотр, загрузка и удаление. */

import { useState } from 'react'
import {
  Button,
  FileButton,
  Group,
  Image,
  Modal,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'

import { deletePhoto, uploadPhotos } from '../api/photos'
import type { PhotoRead } from '../api/photos'
import { errorMessage } from '../lib/errors'
import { formatDateTime } from '../lib/format'

/** Лимит бэка: больше 5 фотографий на устройство не принимается. */
export const PHOTO_LIMIT = 5

interface PhotoGalleryProps {
  deviceId: number
  photos: PhotoRead[]
  canUpload: boolean
  canDelete: (photo: PhotoRead) => boolean
  isArchived: boolean
  onChanged: () => void
}

export function PhotoGallery({
  deviceId,
  photos,
  canUpload,
  canDelete,
  isArchived,
  onChanged,
}: PhotoGalleryProps) {
  const [uploading, setUploading] = useState(false)
  const [viewer, setViewer] = useState<PhotoRead | null>(null)
  const [pendingDelete, setPendingDelete] = useState<PhotoRead | null>(null)
  const [deleting, setDeleting] = useState(false)
  const limitReached = photos.length >= PHOTO_LIMIT

  const upload = async (payload: File | File[] | null) => {
    const files = payload === null ? [] : Array.isArray(payload) ? payload : [payload]
    if (files.length === 0) return
    setUploading(true)
    try {
      await uploadPhotos(deviceId, files)
      notifications.show({ message: 'Фотографии загружены', color: 'green' })
      onChanged()
    } catch (cause) {
      notifications.show({ message: errorMessage(cause), color: 'red' })
    } finally {
      setUploading(false)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deletePhoto(pendingDelete.id)
      notifications.show({ message: 'Фотография удалена', color: 'green' })
      setPendingDelete(null)
      onChanged()
    } catch (cause) {
      notifications.show({ message: errorMessage(cause), color: 'red' })
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Stack gap="xs">
      <Group justify="space-between" align="center">
        <Group gap="sm">
          <Text fw={500}>Фотографии</Text>
          <Text size="xs" c="dimmed">
            {photos.length} из {PHOTO_LIMIT}
          </Text>
        </Group>
        {canUpload && !isArchived && (
          <FileButton
            onChange={upload}
            accept="image/jpeg,image/png,image/webp"
            multiple
            disabled={limitReached || uploading}
          >
            {(props) => (
              <Button {...props} size="xs" variant="default" loading={uploading}>
                Добавить фото
              </Button>
            )}
          </FileButton>
        )}
      </Group>

      {canUpload && !isArchived && limitReached && (
        <Text size="xs" c="dimmed">
          Достигнут лимит: не более {PHOTO_LIMIT} фотографий на устройство.
        </Text>
      )}

      {photos.length === 0 ? (
        <Text size="sm" c="dimmed">
          Фотографий пока нет
        </Text>
      ) : (
        <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing="sm">
          {photos.map((photo) => (
            <Stack key={photo.id} gap={4}>
              <Image
                src={photo.thumb_url}
                alt={`Фото устройства от ${photo.uploaded_by.full_name}`}
                radius="sm"
                h={120}
                fit="cover"
                style={{ cursor: 'zoom-in' }}
                onClick={() => setViewer(photo)}
              />
              {canDelete(photo) && !isArchived && (
                <Button
                  size="compact-xs"
                  variant="subtle"
                  color="red"
                  onClick={() => setPendingDelete(photo)}
                >
                  Удалить
                </Button>
              )}
            </Stack>
          ))}
        </SimpleGrid>
      )}

      <Modal
        opened={viewer !== null}
        onClose={() => setViewer(null)}
        title={viewer ? `Фото от ${formatDateTime(viewer.created_at)}` : ''}
        size="xl"
        centered
      >
        {viewer && (
          <Stack gap="xs">
            <Image src={viewer.url} alt="Фотография устройства" radius="sm" />
            <Text size="xs" c="dimmed">
              Загрузил {viewer.uploaded_by.full_name}
            </Text>
          </Stack>
        )}
      </Modal>

      <Modal
        opened={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title="Удалить фотографию?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">Файл будет удалён с диска, событие останется в истории.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setPendingDelete(null)}>
              Отмена
            </Button>
            <Button color="red" loading={deleting} onClick={confirmDelete}>
              Удалить
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
