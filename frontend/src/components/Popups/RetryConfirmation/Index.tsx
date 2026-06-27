import { Banner, Button, Dialog, Flex, Radio } from '@neo4j-ndl/react';
import { RETRY_OPIONS } from '../../../utils/Constants';
import { useFileContext } from '../../../context/UsersFiles';
import { capitalize } from '../../../utils/Utils';
import { BannerAlertProps } from '../../../types';
import { memo } from 'react';

function RetryConfirmationDialog({
  open,
  onClose,
  fileName,
  retryLoading,
  retryHandler,
  alertStatus,
  onBannerClose,
}: {
  open: boolean;
  onClose: () => void;
  fileName: string;
  retryLoading: boolean;
  alertStatus: BannerAlertProps;
  retryHandler: (filename: string, retryoption: string) => void;
  onBannerClose: () => void;
}) {
  const { filesData, setFilesData } = useFileContext();
  const file = filesData.find((c) => c.name === fileName);
  const RetryOptionsForFile =
    file?.status === 'Failed' || file?.status === 'Cancelled'
      ? RETRY_OPIONS
      : RETRY_OPIONS.filter(
          (option) => option !== 'start_from_beginning' && option !== 'start_from_last_processed_position'
        );

  return (
    <Dialog isOpen={open} onClose={onClose}>
      <Dialog.Content>
        <h5 className='max-w-[90%] mb-2'>Reprocess Options</h5>
        <p className='n-body-small mb-4'>
          Choose how to reprocess, then click Continue. After the status changes to &quot;Ready to Reprocess&quot;,
          select the file and click Generate Graph.
        </p>
        {alertStatus.showAlert && (
          <Banner isCloseable onClose={onBannerClose} className='my-4' type={alertStatus.alertType} usage='inline'>
            {alertStatus.alertMessage}
          </Banner>
        )}
        {!file ? (
          <p className='n-body-small'>Could not find file &quot;{fileName}&quot; in the table. Close and try again.</p>
        ) : (
          <Flex flexDirection='column' gap='3'>
            {RetryOptionsForFile.map((o, i) => (
              <Radio
                key={`${o}${i}`}
                onChange={() => {
                  setFilesData((prev) =>
                    prev.map((f) => (f.name === fileName ? { ...f, retryOptionStatus: true, retryOption: o } : f))
                  );
                }}
                htmlAttributes={{ name: 'retryoptions' }}
                isChecked={o === file?.retryOption && file?.retryOptionStatus}
                label={o
                  .split('_')
                  .map((s) => capitalize(s))
                  .join(' ')}
              />
            ))}
          </Flex>
        )}
      </Dialog.Content>
      <Dialog.Actions className='mt-3'>
        <Button onClick={onClose} isDisabled={retryLoading}>
          Cancel
        </Button>
        <Button
          isLoading={retryLoading}
          isDisabled={!file?.retryOption?.length}
          onClick={() => {
            if (file?.name && file?.retryOption) {
              retryHandler(file.name, file.retryOption);
            }
          }}
        >
          Continue
        </Button>
      </Dialog.Actions>
    </Dialog>
  );
}
export default memo(RetryConfirmationDialog);
